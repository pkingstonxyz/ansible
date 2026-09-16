import re
import nltk
from nltk.corpus import cmudict
from typing import NamedTuple

nltk.download('cmudict', quiet=True)
cmu = cmudict.dict()


class Transform(NamedTuple):
    phonemes: list
    letters: str
    pun: str
    examples: str


# Order matters: more specific / longer phoneme sequences come before shorter
# ones that could shadow them (e.g. S+ER+V before a bare ER rule would).
PHONETIC_TRANSFORMS = [
    # /m/ ... /u/ -> "moo"  (glide-tolerant, so /mju/ words like music work)
    Transform(['M', 'UW'],            r'm(?:u|ew|oo|ou|ue|i)', 'moo',     'music, mutex, amuse'),
    # /m/ + /ə/ + /n/ -> "moon"  (the "-ment" in development, environment)
    Transform(['M', 'AH', 'N'],       r'men',                  'moon',    'development, environment'),
    # /m/ + /ɑ/ -> "moo"  (modify, module, monitor)
    Transform(['M', 'AA'],            r'mo',                   'moo',     'modify, modifying, module'),
    # /k/ + /aʊ/ -> "cow"
    Transform(['K', 'AW'],            r'(?:c|k)ou',            'cow',     'count, counter, account'),
    # /b/ + /aɪ/ -> "bovine"
    Transform(['B', 'AY'],            r'b(?:i|y)',             'bovine',  'binary, bios, byte'),
    # /p/ + /æ/ + /s/ -> "pasture"
    Transform(['P', 'AE', 'S'],       r'pass?',                'pasture', 'password, passive'),
    # /s/ + /er/ + /v/ -> "sirloin"
    Transform(['S', 'ER', 'V'],       r'serv',                 'sirloin', 'server, service'),
    # /k/ + /er/ -> "curd"
    Transform(['K', 'ER'],            r'(?:c|k)er',            'curd',    'kernel, concurrent'),
    # /g/ + /r/ + /æ/ + /s/ -> "grass"
    Transform(['G', 'R', 'AE', 'S'],  r'gras',                 'grass',   'grasp'),
    # /k/ + /æ/ -> "cattle"
    Transform(['K', 'AE'],            r'(?:c|k)a',             'cattle',  'category, capacity, cache'),
    # /h/ + /er/ -> "herd"
    Transform(['HH', 'ER'],           r'h(?:erd|urd|eard|er|ur|ear)', 'herd', 'herd, hurdle, heard'),
    # /ʌ/ + /t/ + /er/ -> "udder"
    Transform(['AH', 'T', 'ER'],      r'(?:u|b)tt?er',         'udder',   'utter, butter'),
]

# Glide phonemes (semivowels) that can sneak between a consonant and its
# vowel, e.g. the /j/ in "music" (M Y UW). We skip over these when matching
# so /mju/-style words still get caught.
GLIDES = {'Y', 'W'}


def sequence_matches(phonemes: list, start: int, target_phones: list) -> bool:
    j = start
    for k, target in enumerate(target_phones):
        # Between phonemes, tolerate intervening glides (e.g. music's 'Y').
        if k > 0:
            while j < len(phonemes) and phonemes[j] in GLIDES and phonemes[j] != target:
                j += 1
        if j >= len(phonemes) or phonemes[j] != target:
            return False
        j += 1
    return True


def apply_casing(original: str, replacement: str) -> str:
    if original.isupper():
        return replacement.upper()
    if original.istitle():
        return replacement.capitalize()
    return replacement.lower()


def cowpunch_word(word: str) -> str:
    clean_word = re.sub(r'[^\w]', '', word).lower()
    if clean_word not in cmu:
        return word

    # Strip stress numbers (e.g., 'UW1' -> 'UW')
    phonemes = [re.sub(r'\d', '', p) for p in cmu[clean_word][0]]

    for transform in PHONETIC_TRANSFORMS:
        # Confirm the sound is present anywhere in the word.
        if not any(sequence_matches(phonemes, i, transform.phonemes)
                   for i in range(len(phonemes))):
            continue

        # Then swap the matching run of letters for the pun.
        match = re.search(transform.letters, word, re.IGNORECASE)
        if match:
            start, end = match.span()
            replacement = apply_casing(word[start:end], transform.pun)
            return word[:start] + replacement + word[end:]

    return word


def cowpunch_text(text: str) -> str:
    return "".join(
        token if token.isspace() else cowpunch_word(token)
        for token in re.split(r'(\s+)', text)
    )


# Cow-themed decoration for header/label lines: (prefix to match at the start
# of a line, emoji to prepend, replacement for that prefix). Longest labels
# first so "[DEPRECATION WARNING]" wins over "[WARNING]" and "PLAY RECAP" over
# "PLAY".
LABEL_EMOJI = [
    ('[DEPRECATION WARNING]', '🐄', '[DEPRECATION MOOOOOOOO]'),
    ('RUNNING HANDLER', '🐂', 'RUNNING HERDER'),
    ('PLAY RECAP', '🐄', 'HERD RECAP'),
    ('[WARNING]', '🐮', '[MOOOOOOOO]'),
    ('[ERROR]', '🐂', '[EMOOGENCY]'),
    ('fatal:', '🐂', 'cattlestrophic:'),
    ('failed:', '🐂', 'stampeded:'),
    ('PLAY', '🐄', 'GRAZE'),
    ('TASK', '🐮', 'CHEW'),
]


def cowmoji(text: str) -> str:
    lines = []
    for line in text.split('\n'):
        stripped = line.lstrip()
        for label, emoji, replacement in LABEL_EMOJI:
            if stripped.startswith(label):
                indent = line[:len(line) - len(stripped)]
                rest = stripped[len(label):]
                line = f'{indent}{emoji} {replacement}{rest}'
                break
        lines.append(line)
    return '\n'.join(lines)


if __name__ == '__main__':
    # Demo output when run directly (not on import).
    sample_text = (
        "Please enter your password to modify the binary music file permissions. "
        "Count the kernel modules on the server and grasp the category before you "
        "commit -- utter herd immunity for your account."
    )
    print(cowpunch_text(sample_text))
