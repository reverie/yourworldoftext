How to make it go:
$ git clone http://github.com/reverie/yourworldoftext.git yourworld
$ export PYTHONPATH=`pwd`
$ cd yourworld
$ pip install -r requirements.txt
$ python manage.py syncdb
$ python.manage.py runserver

The lay of the land:
 - Your World of Text is plain Django. Put in your database settings and you should be able to run it locally right away.
 - The contents of a world are represented by 8x16 character Tile objects. These are created lazily.
 - Most of the code (and all the non-trivial stuff) is client-side, in yourworld.js. It uses the JavaScript Module Pattern.
 - The client simply polls the server for updates. This may not be optimal, but it has held up fine.
 - Extra features like links and protected tiles were added "at great expense and at the last minute". The code may reflect this.
 - Input is received via a hidden input field that always has focus. This technique is more robust than detecting keystrokes, and may be useful in other web applications.

Where to take it:
If you want to get involved in Your World of Text, the TODO file lists a variety of incremental improvements that could be made. If, rather, you want to fork the project and go a new direction, here are some ideas: generalize the tile system; implement a client-side scripting language for a LOGO-like accessible programming environment; or make a collaborative brainstorming tool. Whatever it is, feel free email me if I can help in any way.
