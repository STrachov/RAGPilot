"""
Script to fix the document routes formatting issues
"""
import re

# Read the source file
with open('src/backend/app/api/routes/documents.py', 'r') as f:
    content = f.read()

# Fix function signatures with regular expressions
patterns_to_fix = [
    # Function signatures with CurrentUser as the last parameter
    (r'async def (\w+)\((.*?),\s*current_user: Annotated\[User, Depends\((.*?)\)\],\s*\)', 
     r'async def \1(current_user: Annotated[User, Depends(\3)], \2)'),
     
    # Fix session dependencies
    (r'session: SessionDep = Depends\(\),', r'session: SessionDep,'),
    
    # Functions with session and current_user
    (r'async def (\w+)\((.*?),\s*session: SessionDep,\s*current_user: Annotated\[User, Depends\((.*?)\)\],\s*\)', 
     r'async def \1(current_user: Annotated[User, Depends(\3)], session: SessionDep, \2)'),
     
    # Another case with current_user in the middle
    (r'async def (\w+)\((.*?),\s*current_user: Annotated\[User, Depends\((.*?)\)\],\s*session: SessionDep,\s*(.*?)\)', 
     r'async def \1(current_user: Annotated[User, Depends(\3)], session: SessionDep, \2, \4)')
]

# Apply all the patterns
modified_content = content
for pattern, replacement in patterns_to_fix:
    modified_content = re.sub(pattern, replacement, modified_content)

# Write back the modified content
with open('src/backend/app/api/routes/documents.py', 'w') as f:
    f.write(modified_content)

print("Document routes have been fixed!") 