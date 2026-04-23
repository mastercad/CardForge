import sys

with open('scripts/fill_translations.py', 'rb') as f:
    content = f.read().decode('utf-8')

with open('scripts/fill_translations.py', 'w', encoding='utf-8') as f:
    f.write(content)
