BMI Tracker - PythonAnywhere setup

Folder layout (keep it exactly like this):

  bmi_tracker/
    app.py
    requirements.txt
    templates/   login.html, signup.html, forgotpassword.html,
                 main.html, calculator.html, stats.html, progress.html
    static/      style.css

1. Upload the folder
   PythonAnywhere > Files > upload bmi_tracker.zip into /home/YOURUSERNAME/,
   then open a Bash console and run:
     unzip bmi_tracker.zip

2. Install the packages
   In a Bash console:
     cd ~/bmi_tracker
     pip install --user -r requirements.txt

3. Create the web app
   Web tab > Add a new web app > Manual configuration > pick the newest Python.

4. Edit the WSGI file (link on the Web tab) - replace everything with:

     import sys
     path = '/home/YOURUSERNAME/bmi_tracker'
     if path not in sys.path:
         sys.path.insert(0, path)
     from app import app as application

5. Hit the green Reload button, then open YOURUSERNAME.pythonanywhere.com

Notes
- users.csv, user_data.csv and secret_key.txt are created automatically on
  first run. Don't upload your local copies of them unless you want those
  accounts on the live site, and never share secret_key.txt.
- Don't add a /static mapping on the Web tab. The charts are written into
  bmi_tracker/static at runtime and Flask serves them from there.
- To test on your own computer: pip install -r requirements.txt, then
  python app.py
