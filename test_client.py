import unittest

import urllib2
import xml.sax
import api4

from api4 import EnvelopeHandler

XML = """<envelope begin="2009-06-01" size="4407.0"><person id="9601080" name="\xd0\xaf"><dailyExpense date="2009-06-01"><expression></expression><sum>0</sum></dailyExpense><dailyExpense date="2009-06-02"><expression></expression><sum>0</sum></dailyExpense><dailyExpense date="2009-06-03"><expression></expression><sum>0</sum></dailyExpense><dailyExpense date="2009-06-04"><expression></expression><sum>0</sum></dailyExpense><dailyExpense date="2009-06-05"><expression></expression><sum>0</sum></dailyExpense><dailyExpense date="2009-06-06"><expression></expression><sum>0</sum></dailyExpense><dailyExpense date="2009-06-07"><expression></expression><sum>0</sum></dailyExpense></person></envelope>"""

class TestClient(unittest.TestCase):

	def testEnvelope(self):
		is_done = True
		req = urllib2.Request("http://www.4konverta.com/data/k0sh/envelope/2009-06-04")
		req.add_header("4KApplication", api4.API_KEY)
		req.add_header("4KAuth", "demo")
		r = urllib2.urlopen(req)
		self.assertEqual(XML, r.read())

class TestParser(unittest.TestCase):

	""" Unit test for REST client 4konverta.com """

	def testEnvelope(self):
		handler = EnvelopeHandler()
		xml.sax.parseString(XML, handler)

		e = handler.envelope
		self.assertEqual(4407.0, e.size)
		self.assertEqual(7, len(e.daily))
		self.assertEqual("9601080", e.person_id)

if __name__ == "__main__":
	unittest.main()
