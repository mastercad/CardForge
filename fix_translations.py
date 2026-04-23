import re

with open('scripts/fill_translations.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    # Look for patterns like "something „internal" something" and escape the internal quote
    # This is a bit tricky but since the error is usually a quote inside a string:
    # Let's fix the specific known issues first.
    line = line.replace('„Rahmenfarbe"', r'\"Rahmenfarbe\"')
    line = line.replace('„{name}"', r'\"{name}\"')
    new_lines.append(line)

with open('scripts/fill_translations.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
