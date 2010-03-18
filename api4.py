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

import datetime
import sys
import urllib
import xml.sax

from xml.sax.handler import ContentHandler
from google.appengine.api import urlfetch

USER_AGENT = "Konverta4/0.2"
API_KEY = "Demo"
URL_API = "http://www.4konverta.com/data"

def get_color(date):
	""" Возвращает номер цвета дня недели, взависимости от текущей даты """

	t = datetime.date.today();
	if date < t:
		retval = 1
	elif date == t:
		retval = 2
	else:
		retval = 0
	return retval

def date4(s):
    dt = datetime.datetime.strptime(s, "%Y-%m-%d")
    return dt.date()

def fetch_data(username, password, action, ext_url=""):

    assert action in ("userinfo", "envelope", "dailyExpense")

    return urlfetch.fetch(
        url= "%s/%s/%s/%s" % (URL_API, username, action, ext_url),
        headers={
            "User-Agent": USER_AGENT,
            "4KApplication": API_KEY,
            "4KAuth": password,
        },
    )

def parse_data(xmldata, subject):
    handler_factory = {
        "userinfo" : UserInfoHandler,
        "envelope" : EnvelopeHandler,
        "dailyExpense" : DailyExpenseHandler,
    }
    handler = handler_factory[subject]()
    xml.sax.parseString(xmldata, handler)
    return handler.get_result()

def get_user(username, password):
    response = fetch_data(username, password, "userinfo")
    if response.status_code == 401:
        raise Exception("Неправильное имя пользователя или пароль")

    user = parse_data(response.content, "userinfo")
    user.set_login(username, password)

    return user

def get_envelope(user):
    """ Вовзращает конверт в виде списка дневных трат """
    today = datetime.date.today()

    response = fetch_data(user._username, user._password, "envelope", today.strftime("%Y-%m-%d"))
    if response.status_code != 200:
        raise Exception("Сбой получения страницы 'Выполнение', статус: %d" % response.status_code)

    return parse_data(response.content, "envelope")

def get_daily_expense(user, date):
    """ Возвращает дневные траты в виде кортежа (дата, описание, сумма) """

    person_id = user.get_person_id()
    response = fetch_data(user._username, user._password, "dailyExpense", "%s/%s" % (person_id, date))
    if response.status_code != 200:
        raise Exception("Сбой получения страницы 'DailyExpense', статус: %d" % response.status_code)

    return parse_data(response.content, "dailyExpense")

def set_daily_expense(user, date, expression):
    person_id = user.get_person_id()
		
    post_fields = {
        "expression": expression.encode("utf-8"),
	}
    post_data = urllib.urlencode(post_fields)

    result = urlfetch.fetch(
        url="http://www.4konverta.com/data/%s/dailyExpense/%s/%s" % (user._username, person_id, date),
        payload=post_data,
        method=urlfetch.POST,
        headers={
            "User-Agent": USER_AGENT,
            "4KApplication": API_KEY,
            "4KAuth": user._password,
        },
    )

    if result.status_code != 200:
        raise Exception("Сбой во время сохранения дневных трат, статус : %d" % result.status_code)

class Envelope(object):
    def __init__(self, begin, size):
        self.size = size
        self.begin = begin
        self.end = self.begin + datetime.timedelta(days=6)
        self.by_day = self.size / 7
        self.daily = []
        self.person_id = ""

    def __iter__(self):
        self.total = 0
        self.days = 7
        self.current = 0
        return self

    def add_day(self, total, detail):
        rec = (total, detail)
        self.daily.append(rec)

    def next(self):
        if self.current == 7 or len(self.daily) == 0:
            raise StopIteration
        else:
            date = self.begin + datetime.timedelta(days=self.current)
            sum_of_day, detail = self.daily[self.current]

            total_left = (self.size - self.total) / self.days - sum_of_day
			
            self.current += 1
            rec = (date, sum_of_day, detail, get_color(date), total_left)
            return rec


class User(object):
    def __init__(self, username="", password=""):
        self._persons = []
        self._pid = 0
        self.firstday = 1
        self.set_country("", "")
        self.set_currency("", "")
        self.set_login(username, password)

    def set_login(self, username, password):
        self._username = username
        self._password = password

    def append_person(self, pid, name):
        self._persons.append((pid, name))

    def set_country(self, code, name):
        self._country = (code, name)

    def set_currency(self, code, name):
        self.currency = code
        self.currency_name = name

    def get_person_id(self):
        assert len(self._persons) != 0
        p = self._persons[self._pid]
        return p[0]


class BaseHandler(ContentHandler):
    def __init__(self):
        self.accumulator = ""
        ContentHandler.__init__(self)

    def characters(self, ch):
        self.accumulator += ch

    def get_result(self):
        pass


class EnvelopeHandler(BaseHandler):

    def startElement(self, name, attrs):
        if name == "envelope":
            begin = date4(attrs.get("begin", ""))
            size = float(attrs.get("size", "0"))
            self._envelope = Envelope(begin, size)
        elif name == "person":
            self._envelope.person_id = attrs.get("id", "")

    def endElement(self, name):
        if name == "sum":
            self.total = float(self.accumulator)
        elif name == "expression":
            self.detail = self.accumulator
        elif name == "dailyExpense":
            self._envelope.add_day(self.total, self.detail)
        self.accumulator = ""

    def get_result(self):
        return self._envelope


class DailyExpenseHandler(BaseHandler):
    def __init__(self):
        self._expense = [None, None, None]
        BaseHandler.__init__(self)

    def startElement(self, name, attrs):
        if name == "dailyExpense":
            date = date4(attrs.get("date", ""))
            self._expense[0] = date

    def endElement(self, name):
        if name == "sum":
            self._expense[1] = float(self.accumulator)
        elif name == "expression":
            self._expense[2] = self.accumulator
        self.accumulator = ""

    def get_result(self):
        return tuple(self._expense)


class UserInfoHandler(BaseHandler):
    def __init__(self):
        self._user = None
        self._code = None
        BaseHandler.__init__(self)

    def startElement(self, name, attrs):
        if name == "user":
            self._user = User()
        elif name == "person":
            pid = attrs.get("id", "")
            pname = attrs.get("name", "")
            self._user.append_person(pid, pname)
        elif name == "country" or name == "currency":
            self._code = attrs.get("code", "")

    def endElement(self, name):
        if name == "country":
            self._user.set_country(self._code, self.accumulator)
        elif name == "currency":
            self._user.set_currency(self._code, self.accumulator)
        self.accumulator = ""

    def get_result(self):
        return self._user

