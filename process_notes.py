#!/usr/bin/env python

"""
    This script processes each MIMIC note replacing redacted and obvious information
    with appropriate tokens.
"""
import re
from datetime import datetime

def redacorator(func):
    """
    Decorator for replace functions which passes both the original match and
    lower-case version of it to the replace functions. It also checks for
    empty redacted information.
    """
    def replace(match):
        ori = match.group()
        text = match.group().strip().lower()
        if set(ori) == set(' *]['):
            ori = ''
        return func(text, ori)
    return replace

"""
    All replace functions take in the original text and a lower-cased version
    of it. If the seeking part of the text is found, a replacement token is
    is returned, if not the original text is returned.
"""
@redacorator
def replace_names(text, ori):
    r = ori
    if 'name' in text:
        r = 't_name'
        if 'last' in text:
            if 'doctor' in text:
                r = 't_doctor_lastname'
            else:
                r = 't_lastname'
        elif 'first' in text:
            if 'doctor' in text:
                r = 't_doctor_firstname'
            else:
                r = 't_firstname'
        elif 'initials' in text:
            r = 't_initials'
    return r

@redacorator
def replace_places(text, ori):
    r = ori
    if 'hospital' in text:
        r = 't_hospital'
    elif ('company' in text) or ('university/college' in text):
        r = 't_workplace'
    elif 'location' in text:
        r = 't_location'
    elif 'country' in text:
        r = 't_country'
    elif 'state' in text:
        r = 't_state'
    elif ('address' in text) or ('po box' in text):
        r = 't_address'
    return r

@redacorator
def replace_dates(text, ori):
    r = ori
    if re.search(r'\d{4}-\d{0,2}-\d{0,2}', text):
        r = 't_fulldate'
    elif (re.search(r'\d{0,2}-\d{0,2}', text)) or (re.search(r'\d{0,2}\/\d{0,2}', text)) or ('month/day' in text):
        r = 't_monthday'        
    elif 'year' in text or re.search(r'\b\d{4}\b', text):
        r = 't_year'
    elif 'month' in text:
        r = 't_month'
    elif 'holiday' in text:
        r = 't_holiday'
    elif 'date range' in text:
        r = 't_daterange'
    return r

@redacorator
def replace_identifiers(text, ori):
    r = ori
    if ('numeric identifier' in text) or ('pager number' in text):
        r = 't_pager_id'
    elif '(radiology)' in text:
        r = 't_radclip_id'
    elif 'social security number' in text:
        r = 't_ssn'
    elif 'medical record number' in text:
        r = 't_mrn'
    elif 'age over 90' in text:
        r = 't_oldage'
    elif 'serial number' in text:
        r = 't_sn'
    elif 'unit number' in text:
        r = 't_unit_no'
    elif 'md number' in text:
        r = 't_md_no'
    elif 'telephone/fax' in text:
        r = 't_phone'
    elif 'provider number' in text:
        r = 't_provider_no'
    elif 'contact info' in text:
        r = 't_contact_info'
    return r

def replace_redacted(text):
    """
    Function that compiles the redacted pattern and calls all the replace functions
    """
    pat = re.compile(r'\[\*\*(.*?)\*\*\]', re.IGNORECASE)
    
    # replace name types
    text = pat.sub(replace_names, text)
    
    # replace place types
    text = pat.sub(replace_places, text)
    
    # replace date types
    text = pat.sub(replace_dates, text)

    # replace person identifier types
    text = pat.sub(replace_identifiers, text)
    
    return text

@redacorator
def replace_time(text, ori):
    """
    Replace times with divided up tokens representing the hour.
    E.g., 8:20 AM is replaced by t_forenoon
    Replace 2-digit redacted information that precedes time identifier with
    a generic token
    E.g., [**84**] AM is replaced by t_hour
    """
    r = ori
    if '**' in text:
        r = 't_hour'
    else:
        try:
        # handle exceptions with custom rules
            f, s = text.split()
            s = 'am' if s[0] == 'a' else 'pm'
            l, r = f.split(':')
            if l == '' or l == '00':
                if r == '':
                    r = str(0).zfill(2)
                l = str(12)
            if int(l) > 12:
                l = str(int(l) % 12)
            f = ':'.join([l, r])
            text = ' '.join([f, s])

            d = datetime.strptime(text, '%I:%M %p')
            if d.hour >= 0 and d.hour < 4:
                r = 't_midnight'
            elif d.hour >= 4 and d.hour < 8:
                r = 't_dawn'
            elif d.hour >= 8 and d.hour < 12:
                r = 't_forenoon'
            elif d.hour >= 12 and d.hour < 16:
                r = 't_afternoon'
            elif d.hour >=16 and d.hour <20:
                r = 't_dusk'
            else:
                r = 't_night'
        except ValueError:
            pass
    return r

@redacorator
def replace_time2(time, ori):
    r = ori
    if '**' in time:
        r = 't_hour'
    return r    

def replace_misc(text):
    """
    Replaces certain obvious easy to process items in the notes for helping
    downstream modeling
    """    
    # replace different types of "year old" with year_old
    # matches: y.o., y/o, years old. year old, yearold
    text = re.sub(r'\byears? ?old\b|\by(?:o|r)*[ ./-]*o(?:ld)?\b', 't_year_old',
               text, flags=re.IGNORECASE)
    
    # replaces yr, yr's, yrs with years
    text = re.sub(r'\byr[\'s]*\b', 'years', text, re.IGNORECASE)
    
    # replace Pt and pt with patient, and IN/OUT/OT PT with patient
    # Note: PT also refers to physical therapy and physical therapist
    text = re.sub(r'\b[P|p]t.?|\b(IN|OU?T) PT\b', 'patient', text)
    
    text = re.sub(r'\d{0,2}:\d{0,2} \b[A|P]\.?M\.?\b', replace_time, text, flags=re.IGNORECASE)
    text = re.sub(r'\[\*\*(\d{2})\*\*\] \b[a|p].?m.?\b', replace_time, text, flags=re.IGNORECASE)    

    return text

def process_note(text):
    """
    Master function to processes all the notes
    """
    # replace redacted info with tokens
    text = replace_redacted(text)
    
    # misc scrubbing
    text = replace_misc(text)    
    return text