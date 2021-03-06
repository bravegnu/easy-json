#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
EasyJson.py - https://github.com/bacchilu/easy-json

An easy to understand JSON parser.
See the main function for usage sample.


Luca Bacchi <bacchilu@gmail.com> - http://www.lucabacchi.it
"""

import decimal
import string

def charsGenerator(stream, encoding):
    '''
    Generator of characters, given a unicode or a file object with encoding
    '''

    for line in stream:
        for c in line:
            yield c.decode(encoding)


class JsonParserException(Exception):

    pass


class Tokenizer(object):

    def __init__(self, stream, encoding='utf-8'):
        self.content = charsGenerator(stream, encoding)
        self.current = None
        self.in_string = False

    def assertValues(self, values):
        if self.current is None or self.current not in values:
            raise JsonParserException(u'%s not in %s' % (self.current,
                    values))

    def isEnd(self):
        if self.current is not None:
            raise JsonParserException('Wrong character at EOF')

    def next(self):
        for c in self.content:
            self.current = c
            if not self.in_string and self.current.isspace():
                return self.next()
            return self.current
        self.current = None
        return self.current


class JsonParser(object):

    def __init__(
        self,
        s,
        encoding='utf-8',
        valueCb=None,
        ):

        self.tokenizer = Tokenizer(s, encoding)
        self.valueCb = valueCb

    def parse(self):
        self.tokenizer.next()
        ft = {u'{': self.parseObject, u'[': self.parseArray}
        try:
            ret = ft[self.tokenizer.current]()
            self.tokenizer.isEnd()
            return ret
        except KeyError:
            raise JsonParserException(u'Parsing error')

    def parseObject(self):
        ret = {}
        self.tokenizer.assertValues(u'{')
        if self.tokenizer.next() == u'"':
            while True:
                k = self.parseString()
                self.tokenizer.assertValues(u':')
                self.tokenizer.next()
                v = self.parseValue(k)
                ret[k] = v
                if self.tokenizer.current == u',':
                    self.tokenizer.next()
                    continue
                else:
                    break
        self.tokenizer.assertValues(u'}')
        self.tokenizer.next()
        return ret

    def parseArray(self):
        ret = []
        self.tokenizer.assertValues(u'[')
        if self.tokenizer.next() != u']':
            while True:
                ret.append(self.parseValue(None))
                if self.tokenizer.current == u',':
                    self.tokenizer.next()
                    continue
                else:
                    break
        self.tokenizer.assertValues(u']')
        self.tokenizer.next()
        return ret

    def parseString(self):
        ret = u''
        self.tokenizer.in_string = True
        self.tokenizer.assertValues(u'"')
        while True:
            self.tokenizer.next()
            if self.tokenizer.current == u'"':
                break
            elif self.tokenizer.current == u'\\':
                self.tokenizer.next()
                if self.tokenizer.current == u'u':
                    exValue = 0
                    for i in range(4):
                        self.tokenizer.next()
                        self.tokenizer.assertValues(u'0123456789abcdefABCDEF'
                                )
                        exValue *= 16
                        exValue += int(self.tokenizer.current, 16)
                    ret += unichr(exValue)
                else:
                    c = {
                        u'"': u'"',
                        u'\\': u'\\',
                        u'/': u'/',
                        u'b': u'\b',
                        u'f': u'\f',
                        u'n': u'\n',
                        u'r': u'\r',
                        u't': u'\t',
                        }
                    try:
                        ret += c[self.tokenizer.current]
                    except KeyError:
                        raise JsonParserException(u'Wrong control character'
                                )
            elif ord(self.tokenizer.current) >= 32:
                ret += self.tokenizer.current
            else:
                raise JsonParserException(u'Wrong character in string')
        self.tokenizer.assertValues(u'"')
        self.tokenizer.in_string = False
        self.tokenizer.next()
        return ret

    def parseValue(self, key):
        if self.tokenizer.current.isdigit():
            ret = self.parseNumber()
        else:
            d = {
                u'-': self.parseNumber,
                u'"': self.parseString,
                u'{': self.parseObject,
                u'[': self.parseArray,
                u't': self.parseTrue,
                u'f': self.parseFalse,
                u'n': self.parseNull,
                }
            try:
                ret = d[self.tokenizer.current]()
            except KeyError:
                raise JsonParserException(u'Wrong character in value')
        if self.valueCb is not None:
            return self.valueCb(key, ret)
        return ret

    def parseTrue(self):
        self.tokenizer.assertValues(u't')
        self.tokenizer.next()
        self.tokenizer.assertValues(u'r')
        self.tokenizer.next()
        self.tokenizer.assertValues(u'u')
        self.tokenizer.next()
        self.tokenizer.assertValues(u'e')
        self.tokenizer.next()
        return True

    def parseFalse(self):
        self.tokenizer.assertValues(u'f')
        self.tokenizer.next()
        self.tokenizer.assertValues(u'a')
        self.tokenizer.next()
        self.tokenizer.assertValues(u'l')
        self.tokenizer.next()
        self.tokenizer.assertValues(u's')
        self.tokenizer.next()
        self.tokenizer.assertValues(u'e')
        self.tokenizer.next()
        return False

    def parseNull(self):
        self.tokenizer.assertValues(u'n')
        self.tokenizer.next()
        self.tokenizer.assertValues(u'u')
        self.tokenizer.next()
        self.tokenizer.assertValues(u'l')
        self.tokenizer.next()
        self.tokenizer.assertValues(u'l')
        self.tokenizer.next()
        return None

    def parseNumber(self):
        ret = decimal.Decimal(0)
        sign = 1
        self.tokenizer.assertValues(u'-0123456789')
        if self.tokenizer.current == u'-':
            sign = -1
            self.tokenizer.next()
        if self.tokenizer.current == u'0':
            self.tokenizer.next()
        else:
            self.tokenizer.assertValues(u'123456789')
            ret = decimal.Decimal(int(self.tokenizer.current))
            while self.tokenizer.next().isdigit():
                ret *= 10
                ret += int(self.tokenizer.current)

        if self.tokenizer.current.isdigit():
            raise JsonParserException("Wrong character in number")

        if self.tokenizer.current == u'.':
            self.tokenizer.next()
            self.tokenizer.assertValues(u'0123456789')
            fraction = decimal.Decimal(10)
            while self.tokenizer.current.isdigit():
                ret += decimal.Decimal(self.tokenizer.current) \
                    / fraction
                fraction *= 10
                self.tokenizer.next()
        if self.tokenizer.current in (u'e', u'E'):
            eSign = 1
            self.tokenizer.next()
            if self.tokenizer.current == u'+':
                eSign = 1
                self.tokenizer.next()
            elif self.tokenizer.current == u'-':
                eSign = -1
                self.tokenizer.next()
            self.tokenizer.assertValues(u'0123456789')
            exp = decimal.Decimal(int(self.tokenizer.current))
            while self.tokenizer.next().isdigit():
                exp *= 10
                exp += int(self.tokenizer.current)
            ret = ret * 10 ** (exp * eSign)
        return ret * sign


def loads(json, encoding='utf-8', valueCb=None):
    return JsonParser(json, encoding, valueCb).parse()


class JsonVisitor(object):

    def dumps(self, pyJson):
        if isinstance(pyJson, dict):
            return self.dumpDict(pyJson)
        if isinstance(pyJson, list):
            return self.dumpList(pyJson)
        raise JsonParserException('Wrong Python argument')

    def dumpDict(self, pyJson):
        assert isinstance(pyJson, dict)
        resultString = u'{'
        resultString += u', '.join(self.dumpString(k) + u': '
                                   + self.dumpValue(v) for (k, v) in
                                   pyJson.iteritems())
        resultString += u'}'
        return resultString

    def dumpList(self, pyJson):
        assert isinstance(pyJson, list)
        resultString = u'['
        resultString += u', '.join(self.dumpValue(e) for e in pyJson)
        resultString += u']'
        return resultString

    def dumpString(self, pyJson):
        assert isinstance(pyJson, unicode)
        resultString = u'"'
        for c in pyJson:
            charDict = {
                u'"': u'\\"',
                u'\\': u'\\\\',
                u'/': u'\\/',
                u'\b': u'\\b',
                u'\f': u'\\f',
                u'\n': u'\\n',
                u'\r': u'\\r',
                u'\t': u'\\t',
                }
            try:
                resultString += charDict[c]
            except KeyError:
                if c in string.printable:
                    resultString += c
                else:
                    resultString += u"\\u%04x" % ord(c)
        resultString += u'"'
        return resultString

    def dumpValue(self, pyJson):
        if isinstance(pyJson, unicode):
            return self.dumpString(pyJson)
        if isinstance(pyJson, decimal.Decimal):
            return self.dumpNumber(pyJson)
        if isinstance(pyJson, bool):
            return pyJson and u'true' or u'false'
        if isinstance(pyJson, int):
            return self.dumpNumber(pyJson)
        if isinstance(pyJson, float):
            return self.dumpNumber(pyJson)
        if isinstance(pyJson, dict):
            return self.dumpDict(pyJson)
        if isinstance(pyJson, list):
            return self.dumpList(pyJson)
        if pyJson is None:
            return u'null'
        raise JsonParserException('Wrong Python argument')

    def dumpNumber(self, pyJson):
        return unicode(pyJson)


def dumps(pyJson):
    return JsonVisitor().dumps(pyJson)


def pyEncode(elem, encoding):
    if isinstance(elem, dict):
        return dict((pyEncode(k, encoding), pyEncode(v, encoding))
                    for (k, v) in elem.iteritems())
    if isinstance(elem, list):
        return [pyEncode(e, encoding) for e in elem]
    if isinstance(elem, unicode):
        return elem.encode(encoding)
    return elem


def pyDecode(elem, encoding):
    if isinstance(elem, dict):
        return dict((pyDecode(k, encoding), pyDecode(v, encoding))
                    for (k, v) in elem.iteritems())
    if isinstance(elem, list):
        return [pyDecode(e, encoding) for e in elem]
    if isinstance(elem, str):
        return elem.decode(encoding)
    return elem


if __name__ == '__main__':
    json = \
        u'{"compleanno": 182214000, "born": "11/10/1975", "Luca\\n": "A\\u1234B", "luca": {}, "a": true, "False": false, "null": null, "lica": ["Luca", {}], "1": 12.4e-2, "Luca Bacchi": "Bacchi Luca"}'

    import StringIO
    import pprint


    def dateParser(k, v):
        import datetime

        if k == u'compleanno':
            assert isinstance(v, decimal.Decimal)
            return datetime.datetime.fromtimestamp(int(v))

        if not isinstance(v, unicode):
            return v
        try:
            return datetime.datetime.strptime(v, u'%d/%m/%Y')
        except ValueError:
            return v


    print 'STRING'
    pyJson = loads(json, valueCb=dateParser)
    pprint.pprint(pyJson)
    print

    print 'STREAM'
    pyJson = loads(StringIO.StringIO(json.encode('utf-8')), 'utf-8')
    pprint.pprint(pyJson)
    print

    print 'FILE'
    with open('stream.json') as fp:
        pprint.pprint(loads(fp, 'utf-8'))
    print

    pprint.pprint(pyEncode(pyJson, 'utf-8'))
    pprint.pprint(dumps(pyJson))

    pprint.pprint(pyDecode({'luca': 'bacchi'}, 'utf-8'))
