import re


def is_valid_reference(text):
    pattern = r'\d+\s*[A-Za-z&\s\.\-]+,\s*\d{4}'
    return bool(re.match(pattern, text))
print(is_valid_reference("1Idjradinata & Pollitt, 1993, 2 EFSA opinions 2009 7(9):1215 and Q-2008-325​, 3McCann et al., 2020"))