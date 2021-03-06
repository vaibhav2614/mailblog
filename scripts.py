# vim: set expandtab sw=4 ts=4 softtabstop=4 autoindent smartindent:
from secrets import imap_username, imap_password, imap_host
import imaplib
import email
import requests
import re
from email_remover import unquote

site_url = 'http://0.0.0.0:8888'

def get_text_block(email_message):
    maintype = email_message.get_content_maintype()
    if maintype == 'multipart':
        for part in email_message.get_payload():
            if part.get_content_maintype() == 'text':
                return part.get_payload()
    elif maintype == 'text':
        return email_message.get_payload()

def get_html_block(email_message):
    maintype = email_message.get_content_type()
    if maintype == 'multipart':
        for part in email_message.get_payload():
            if part.get_content_type() == 'text/html':
                return part.get_payload()
    elif maintype == 'text/html':
        return email_message.get_payload()

def remove_quoted_text(email):
    spacers = "[\s,/\.\-]"

    day_pattern = "(?:(?:Mon(?:day)?)|(?:Tue(?:sday)?)|(?:Wed(?:nesday)?)|(?:Thu(?:rsday)?)|(?:Fri(?:day)?)|(?:Sat(?:urday)?)|(?:Sun(?:day)?))";

    time_pattern  = "(?:[0-2])?[0-9]:[0-5][0-9](?::[0-5][0-9])?(?:(?:\s)?[AP]M)?"

    day_of_month_pattern = "[0-3]?[0-9]" + spacers + "*(?:(?:th)|(?:st)|(?:nd)|(?:rd))?"


    month_pattern = "(?:(?:Jan(?:uary)?)|(?:Feb(?:uary)?)|(?:Mar(?:ch)?)|(?:Apr(?:il)?)|(?:May)|(?:Jun(?:e)?)|(?:Jul(?:y)?)|(?:Aug(?:ust)?)|(?:Sep(?:tember)?)|(?:Oct(?:ober)?)|(?:Nov(?:ember)?)|(?:Dec(?:ember)?)|(?:[0-1]?[0-9]))";

    year_pattern = "(?:[1-2]?[0-9])[0-9][0-9]"

    date_pattern = "(?:" + day_pattern + spacers + "+)?(?:(?:" + day_of_month_pattern + spacers + "+" + month_pattern + ")|" + "(?:" + month_pattern + spacers + "+" + day_of_month_pattern + "))" + spacers + "+" + year_pattern

    date_time_pattern = "(?:" + date_pattern + "[\s,]*(?:(?:at)|(?:@))?\s*" + time_pattern + ")|" + "(?:" + time_pattern + "[\s,]*(?:on)?\s*"+ date_pattern + ")"
    date_time_pattern = '.*'


    lead_in_line = "-+\s*(?:Original(?:\sMessage)?)?\s*-+\n"

    date_line = "(?:(?:date)|(?:sent)|(?:time)):\s*"+ date_time_pattern + ".*\n"

    subject_or_address_line = "((?:from)|(?:subject)|(?:b?cc)|(?:to))|:.*\n"

    #gmail_quoted_text_beginning = "(On\s+" + date_time_pattern + ".*wrote:\n)"
    gmail_quoted_text_beginning = "(On\s+" + date_time_pattern + ".*wrote:\n)"

    quoted_text_beginning = re.compile("(?i)(?:(?:" + lead_in_line + ")?" + "(?:(?:" +subject_or_address_line + ")|(?:" + date_line + ")){2,6})|(?:" + gmail_quoted_text_beginning + ")")

    result = re.search(quoted_text_beginning, email)
    if result:
        return email[:result.start()]

    return result

def imap_populate():
    """ Populates the database from imap."""

    mail = imaplib.IMAP4_SSL(imap_host)
    mail.login(imap_username, imap_password)
    mail.list()
    mail.select('[Gmail]/All Mail')

    status, email_ids = mail.search(None, '(TO "ru_cs@googlegroups.com")')

    i = 0

    for email_id in reversed(email_ids[0].split()):
        typ, data = mail.fetch(email_id, '(RFC822)')

        email_parsed = email.message_from_string(data[0][1])
        #email_text = email_parsed.get_payload()[0].get_payload()
        email_text = get_text_block(email_parsed)
        html_text = get_html_block(email_parsed)

        if not html_text:
            html_text = email_text

        if email_text: 
            unquoted_text = remove_sig(unquote(email_text))
            unquoted_html = remove_sig(unquote(html_text))

            _from = email_parsed.get('From')
            subject = email_parsed.get('Subject')
            time = email_parsed.get('Date')

            print unquoted_html
            print "Subject: ", subject

            if subject and _from:
                mock_email(_from, 'ru_cs@googlegroups.com', subject, unquoted_text, unquoted_html, time=time)
        i += 1
def mock_email(_from, to, subject, text, html=None, time=None, attachments=None):
    if not html:
        html = text

    if not attachments:
        attachments = []

    files = {}
    for attachment in attachments:
        files[attachment] = open(attachment, 'rb').read()

    email_object = {
        'from': _from,
        'html': html,
        'subject': subject,
        'text': text,
        'to': to,
        'time': time,
        'attachments': len(attachments),
    }

    r = requests.post(site_url+'/callback', data=email_object, files=files)
    assert r.status_code == 200

def reset_db():
    from app import db
    from models import User, Email
    User.drop_table()
    User.create_table()

    Email.drop_table()
    Email.create_table()

def remove_sig(email):
    sig = '(\s+--(=20)*\s+.*)'

    regex = re.compile(sig, flags=re.DOTALL)
    m = re.search(regex, email)
    if m:
        return email[:m.start()]
    return email

if __name__ == '__main__':
    mock_email('Herp <herp@herp.com>', 'ru_cs@googlegroups.com', 'herp', '<img src="http://www.google.com/images/srpr/logo3w.png" alt="testmebro" />')
    # reset_db()
    # imap_populate()
