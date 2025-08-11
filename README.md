# Notion-style Flask App (Pretty UI + Allow/Block ACL)

Features:
- User registration / login (Flask-Login)
- Notes with UUID routes
- ACL: Allow group + Block group (block takes precedence)
- Pretty UI for ACL: tabs, search & add, mutual exclusion between allow/block
- Ready for PythonAnywhere and GitHub

## Quick Start (local)
```bash
git clone <repo>
cd notion_acl_pretty
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp instance/config.py.example instance/config.py
# edit SECRET_KEY in instance/config.py
flask run
```

## PythonAnywhere
- Upload or git clone repo to your home directory
- In Web tab, point source to project directory
- Set WSGI to import `app` from `app.py`
- Ensure `instance/config.py` has SECRET_KEY (do not commit it)
