#!/usr/bin/env python
# -*- mode: python; coding: utf-8; -*-
#
# copyright (c) 2009 renat nasyrov <renatn@gmail.com>.
#
# this file is part of konverta4.
#
# konverta4 is free software: you can redistribute it and/or modify
# it under the terms of the gnu general public license as published by
# the free software foundation, either version 3 of the license, or
# (at your option) any later version.
#
# konverta4 is distributed in the hope that it will be useful,
# but without any warranty; without even the implied warranty of
# merchantability or fitness for a particular purpose.  see the
# gnu general public license for more details.
#
# you should have received a copy of the gnu general public license
# along with konverta4.  if not, see <http://www.gnu.org/licenses/>.

import cgi
import cPickle
import datetime
import hashlib
import logging
import os
import random
import wsgiref.handlers
import xml.sax
import api4
import StringIO

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import urlfetch
from google.appengine.api import memcache

def auth_required(func):
    """ Декоратор, проверяющий авторизацию пользователя,
        перед доступом к странице """

    def wrapper(self):
        session = self.get_session()
        if not session:
            self.redirect("/login")
        else:
            return func(self)
    return wrapper


class BaseHandler(webapp.RequestHandler):
    
    def get_sid(self):
        if self.request.cookies.has_key("sid"):
            return self.request.cookies["sid"]
        return ""

    def get_session(self):
        sid = self.get_sid()
        return memcache.get("sid-" + sid)

    def get_user(self):
        session = self.get_session()
        buf = StringIO.StringIO(session)
        user = cPickle.load(buf)
        buf.close()
        return user

    def error500(self, msg):
        logging.error(msg)
        self.error(500)
        self.response.out.write("<html><body><h2>%s</h2></body></html>" % msg)


class MainPage(BaseHandler):

    def get(self):

        path = os.path.join(os.path.dirname(__file__), "templates/envelope.html")
        self.response.out.write(template.render(path, {}))


class DailyPage(BaseHandler):

    @auth_required
    def get(self):

        date = cgi.escape(self.request.get("date"))
        user = self.get_user()

        try:
            expense = api4.get_daily_expense(user, date)
        except Exception, e:
            self.error500(e)
            return
        
        template_values = {
            "expense" : expense,
        }
        path = os.path.join(os.path.dirname(__file__), "daily.html")
        self.response.out.write(template.render(path, template_values))


class UpdateHandler(BaseHandler):

    @auth_required
    def post(self):
        expr = cgi.escape(self.request.get("expr"))
        date = cgi.escape(self.request.get("date"))
        user = self.get_user()

        try:
            api4.set_daily_expense(user, date, expr)
        except Exception, msg:
            self.error500(msg)
            return

        self.redirect("/")

class LoginPage(BaseHandler):

    def new_sid(self):
        """ Генерирует новый Session ID """

        v = datetime.datetime.now().strftime("%s") + str(random.random())
        h = hashlib.md5()
        h.update(v)
        return h.hexdigest()

    def set_session(self, session, rmbr):
        """ Устанавливает куки с новым Session ID,
            и сохраняет сессию в memcache """
        
        sid = self.new_sid()
        t = 900
        if  rmbr != "":
            t = 3600*24*7

        expires = datetime.datetime.now() + datetime.timedelta(seconds=t)
        expires_rfc822 = expires.strftime('%a, %d %b %Y %H:%M:%S +0000')

        cookie = "sid=%s; path=/; expires=%s" % (sid, expires_rfc822)
        self.response.headers.add_header("Set-Cookie", cookie)

        if not memcache.set(key="sid-"+sid, value=session, time=t):
            logging.error("Memcache set session failed")


    def do_logout(self):
        """ Выполняет Logout пользователя из сервиса """

        sid = self.get_sid()
        memcache.delete("sid-" + sid)

    def serialize_user(self, user):
        buf = StringIO.StringIO()
        cPickle.dump(user, buf)
        user_str = buf.getvalue()
        buf.close()
        return user_str

    def get(self):
        if self.request.path == "/logout":
            self.do_logout()
            self.redirect("/login")
            return

        path = os.path.join(os.path.dirname(__file__), "templates/login.html")
        self.response.out.write(template.render(path, {}))

    def post(self):
        uname = cgi.escape(self.request.get("username"))
        passwd = cgi.escape(self.request.get("password"))
        rmbr = self.request.get("remember")
        try:
            user = api4.get_user(uname, passwd)
        except Exception, msg:
            self.redirect("/login?err=%s" % msg)
            return

        session = self.serialize_user(user)

        self.set_session(session, rmbr)
        self.redirect("/")

def main():
    application = webapp.WSGIApplication(
            [("/", MainPage),
            ("/daily", DailyPage),
            ("/update", UpdateHandler),
            ("/login", LoginPage),
            ("/logout", LoginPage)],
            debug=True)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
    main()
