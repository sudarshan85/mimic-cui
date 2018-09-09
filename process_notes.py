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
#         if set(ori) == set(' *]['):
#             ori = ''
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
        r = 'xxname'
        if 'last' in text:
            if 'doctor' in text:
                r = 'xxdocln'
            else:
                r = 'xxln'
        elif 'first' in text:
            if 'doctor' in text:
                r = 'xxdocfn'
            else:
                r = 'xxfn'
        elif 'initials' in text:
            r = 'xxinit'
    return r

@redacorator
def replace_places(text, ori):
    r = ori
    if 'hospital' in text:
        r = 'xxhosp'
    elif ('company' in text) or ('university/college' in text):
        r = 'xxwork'
    elif 'location' in text:
        r = 'xxloc'
    elif 'country' in text:
        r = 'xxcntry'
    elif 'state' in text:
        r = 'xxstate'
    elif ('address' in text) or ('po box' in text):
        r = 'xxaddr'
    return r

@redacorator
def replace_dates(text, ori):
    r = ori
    if re.search(r'\d{4}-\d{0,2}-\d{0,2}', text):
        r = 'xxdate'
    elif (re.search(r'\d{0,2}-\d{0,2}', text)) or (re.search(r'\d{0,2}\/\d{0,2}', text)) or ('month/day' in text):
        r = 'xxmmdd'        
    elif 'year' in text or re.search(r'\b\d{4}\b', text):
        r = 'xxyear'
    elif 'month' in text:
        r = 'xxmnth'
    elif 'holiday' in text:
        r = 'xxhols'
    elif 'date range' in text:
        r = 'xxdtrnge'
    return r

@redacorator
def replace_identifiers(text, ori):
    r = ori
    if ('numeric identifier' in text) or ('pager number' in text):
        r = 'xxpager'
    elif '(radiology)' in text:
        r = 'xxradclip'
    elif 'social security number' in text:
        r = 'xxssn'
    elif 'medical record number' in text:
        r = 'xxmrno'
    elif 'age over 90' in text:
        r = 'xxage90'
    elif 'serial number' in text:
        r = 'xxsno'
    elif 'unit number' in text:
        r = 'xxunitno'
    elif 'md number' in text:
        r = 'xxmdno'
    elif 'telephone/fax' in text:
        r = 'xxph'
    elif 'provider number' in text:
        r = 'xxpno'
    elif 'job number' in text:
        r = 'xxjobno'
    elif 'dictator info' in text:
        r = 'xxdicinfo'        
    elif 'contact info' in text:
        r = 'xxcntinfo'
    elif 'attending info' in text:
        r = 'xxattinfo'        
    return r

@redacorator
def replace_digits(text, ori):
    r = ori
    if re.search(r'\d\d\d', text):
        r = 'xx3digit' 
    elif re.search(r'\d\d', text):
        r = 'xx2digit'
    elif re.search(r'\d', text):
        r = 'xx1digit'
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
    
    # replace person identifier types
    text = pat.sub(replace_identifiers, text)    
    
    # replace date types
    text = pat.sub(replace_dates, text)
    
    # replace remaining digits
    text = pat.sub(replace_digits, text)
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
        r = 'xxhour'
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
                r = 'xxmidngt'
            elif d.hour >= 4 and d.hour < 8:
                r = 'xxdawn'
            elif d.hour >= 8 and d.hour < 12:
                r = 'xxfore'
            elif d.hour >= 12 and d.hour < 16:
                r = 'xxafter'
            elif d.hour >=16 and d.hour <20:
                r = 'xxdusk'
            else:
                r = 'xxngt'
        except ValueError:
            pass
    return r

def replace_misc(text):
    """
    Replaces certain obvious easy to process items in the notes for helping
    downstream modeling
    """    
    # replace different types of "year old" with year_old
    # matches: y.o., y/o, years old. year old, yearold
    text = re.sub(r'-?\byears? ?-?old\b|\by(?:o|r)*[ ./-]*o(?:ld)?\b', ' years old', text, flags=re.IGNORECASE)
    
    # replaces yr, yr's, yrs with years
    text = re.sub(r'\byr[\'s]*\b', 'years', text, re.IGNORECASE)
    
    # replace Pt and pt with patient, and IN/OUT/OT PT with patient
    # Note: PT also refers to physical therapy and physical therapist
    text = re.sub(r'\b[P|p]t.?|\b(IN|OU?T) PT\b', 'patient ', text)
    
    # replace time types
    text = re.sub(r'\d{0,2}:\d{0,2} \b[A|P]\.?M\.?\b', replace_time, text, flags=re.IGNORECASE)
    text = re.sub(r'\[\*\*(\d{2})\*\*\] \b[a|p].?m.?\b', replace_time, text, flags=re.IGNORECASE)
    
#     text = re.sub(r'\[\*\*(.*?)\*\*\]', '', text, flags=re.IGNORECASE)

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