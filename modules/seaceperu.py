import re
from bs4 import BeautifulSoup
import urllib2
import datetime
from string import replace

class SEACE:
    INTEREST_SUBSET = 1
    INTEREST_LEAD = 2
    INTEREST_NOT = 5
    INTEREST_OPPORTUNITY = 3
    INTEREST_HOT = 4

    INTEREST = { None:"cleardot.gif", INTEREST_SUBSET:"cleardot.gif",
        INTEREST_NOT:"not.png", INTEREST_LEAD:"star_lit_purple_question3.png",
        INTEREST_OPPORTUNITY:"star-lit4.png", INTEREST_HOT:"star_lit_yellow_bang3.png" }

    SEARCH_URI = "http://www2.seace.gob.pe/Default.asp?_CALIFICADOR_=PORTLET.1.47.0.3.10&_REGIONID_=1&_PORTLETID_=47&_PRIVILEGEID_=5&_ORDERID_=0&_PAGEID_=3&_CONTENTID_=10&_USERID_=%3C%21--USERID--%3E&_EVENTNAME_=&_OBJECTFIRE_=&_OBJECTEVENT_=&scriptdo=pku_opnegocio.doviewoportunidades&lpanhoentidad=2013"

    DETAIL_URI = "http://www.seace.gob.pe/openasportlet.asp?scriptdo=pku_opnegocio.doviewficha&_CALIFICADOR_=PORTLET.0.47.0.0.0&_REGIONID_=0&_PORTLETID_=47&_ORDERID_=0&_PAGEID_=0&_CONTENTID_=0&_USERID_=%3C!--@USERID--%3E&_PRIVILEGEID_=5"

    NOTIFICACION_URI = "http://www2.seace.gob.pe/openasportlet.asp?_portletid_=47&scriptdo=pku_opnegocio.dodetallenotificacion"

    HTTP_TIMEOUT = 10

    @staticmethod
    def cycle_interest_level(level):
        if level in (SEACE.INTEREST_SUBSET, SEACE.INTEREST_NOT, SEACE.INTEREST_LEAD):
            newlevel = SEACE.INTEREST_OPPORTUNITY
        elif level == SEACE.INTEREST_OPPORTUNITY:
            newlevel = SEACE.INTEREST_HOT
        elif level == SEACE.INTEREST_HOT:
            newlevel = SEACE.INTEREST_NOT
        else:
            print "cycle_interest_level(): unexpected value %d. Unchanged" % level
            return level
        return newlevel

    @classmethod
    def build_search_uri(cls, sintesis=None, modification_date=None):
        if not sintesis and not modification_date:
            return None
        result = cls.SEARCH_URI
        if sintesis:
            result += "&lpitem_descripcion=" + sintesis
        if modification_date:
            result += "&lpf_registro=" + modification_date.strftime("%d/%m/%Y")
        return result

    @classmethod
    def build_detail_uri(cls, num_convocatoria):
        return cls.DETAIL_URI + "&lpnconvoca=" + num_convocatoria if num_convocatoria else None

    @classmethod
    def build_notificacion_uri(cls, num_notificacion, anho_notificacion):
        if num_notificacion and anho_notificacion:
            return cls.NOTIFICACION_URI + "&ag_notificacion=" + num_notificacion + "&ag_anhonotificacion=" + anho_notificacion
        else:
            return None

    @classmethod
    def get_page(cls, uri):
        if not uri:
            return None
        try:
            result = urllib2.urlopen(uri, timeout=cls.HTTP_TIMEOUT)
        except:
            print "get_page(): urllib2 Timeout?"
            return None
        if not result:
            return None
        try:
            result = result.read()
        except:
            print "get_page(): socket or read error?"
            return None
        return result

    @classmethod
    def search_words(cls, text):
        wordlist = re.findall('(\w+)', text.upper())
        results = set()
        for word in wordlist:
            print "Searching for term", word + "..."
            convocatorias = cls.search(cls.build_search_uri(sintesis=word))
            if convocatorias:
                print len(convocatorias), "results."
                results.update(convocatorias)
            else:
                print "zero results."
        print "Union of all results:", len(results), "results."
        return results

    @classmethod
    def search_date(cls, d):
        print "Searching for modification date", d.strftime("%d/%m/%Y")
        result = cls.search(cls.build_search_uri(modification_date=d))
        print len(result), "results."
        return result

    @classmethod
    def search(cls, uri):
        page = cls.get_page(uri)
        if not page:
            return []
        pages = []
        pages.append(page)
        s = re.split('P&aacute;ginas', page, 1, re.S)
        if len(s) > 1:
            pageparams = re.findall('(&lppagenum=\d+)', s[1], re.S)
            print len(pageparams)+1, "pages of results."
            for pageparam in pageparams:
                page = cls.get_page(uri+pageparam)
                if page:
                    pages.append(page)
        results = set()
        for p in pages:
            results.update(cls.get_convocatorias_from_search_page(p))
        return results

    @classmethod
    def get_convocatorias_from_search_page(cls, p):
        if not p:
            return None
        l = re.findall('lpnconvoca,(\d+),.+?(\d+/\d+/\d+ \d+:\d+)', p, re.S)
        return map(cls.stod,l)

    @staticmethod
    def stod(key):
        return (key[0], datetime.datetime.strptime(key[1], "%d/%m/%Y %H:%M")) if key else None

    @classmethod
    def get_convocatorias(cls, db, items):
        if not items:
            return 0
        itemlist = items if type(items) == list or type(items) == set else [items]
        queue = len(itemlist)
        result = 0
        for i in itemlist:
            print "Queue contains", queue, "items."
            if cls.get_convocatoria(db, i):
                result += 1
            queue -= 1
        print "Queue empty."
        return result

    @classmethod
    def get_convocatoria(cls, db, item):
        Process = db.seace_process
        Interest = db.seace_interest
        Event = db.seace_event
        Action = db.seace_action
        Item = db.seace_item
#        print "Item requested", item[0], "dated", item[1] + "with type", type(item[1]), "..."
        cache = Process(Process.num_convocatoria == item[0])
        if cache:
            process_id = cache['id']
            query = ((Interest.process == process_id) &
                    (Interest.interest_level.belongs((SEACE.INTEREST_OPPORTUNITY, SEACE.INTEREST_HOT))))
            interested = db(query).count()
            last_updated_on = cache.get('last_updated_on')
            if interested == 0 and last_updated_on:
                if last_updated_on == item[1]:
                    print "Good cache found. Skipped."
                    return False
                elif last_updated_on > item[1]:
                    print "get_convocatoria(): Warning... cache has more recent last_updated_on than Seace database's record! Not updating."
                    return False
        print "Downloading item", item[0] + "..."
        pages = []
        uri = cls.build_detail_uri(item[0])
        pages.append(cls.get_page(uri))

        if not pages[0]:
            print "get_convocatoria(): empty page 0"
            return False

        # get additional pages if any
        s = re.split('P&aacute;ginas', pages[0], 1, re.S)
        if s:
            for pageparam in re.findall('(&pnpage=\d+)', s[1], re.S):
                page = cls.get_page(uri+pageparam)
                if page:
                    pages.append(page)
        c = SeaceConvocatoria(pages)
        if not c.num_convocatoria:
            print "Item", item[0], "could not be parsed."
            return False

        if cache:
            print "Updating convocatoria", c.num_convocatoria + "..."
            pass
        else:
            print "Inserting convocatoria", c.num_convocatoria + "..."
            pass
        id_proceso = Process.update_or_insert(Process.num_convocatoria == c.num_convocatoria,
            num_convocatoria=c.num_convocatoria, last_updated_on = item[1],
            nombre=c.nombre, entidad=c.entidad, direccion=c.direccion, sintesis=c.sintesis,
            objeto=c.objeto, moneda=c.moneda, monto=c.monto, ultima_etapa=c.ultima_etapa,
            last_action=c.last_action, last_action_on=c.last_action_on,
            items_text=c.items_text, enlace=uri, html_text=c.html_text, action_html=c.action_html,
            cached_on=datetime.datetime.now())
        if cache:
            id_proceso = cache['id']
            existingcalendar = db(Event.proceso==id_proceso).select(Event.hito,
                Event.tipo, Event.fecha).as_list()
            if c.events == existingcalendar:
                print "get_convocatoria(): new calendar and cached calendar are identical."
            else:
                # when pulled from database into a list of dict's, dates are converted to strings.
                # so dicts do not match.
                print "c.events and existingcalendar DO NOT MATCH."
#                print "c.events =", c.events
#                print "existingcalendar =", existingcalendar
        db(Event.proceso==id_proceso).delete()
        l = list(c.events)
        for e in l:
            e.update({'proceso': id_proceso})
        Event.bulk_insert(l)
        
        db(Action.proceso==id_proceso).delete()
        l = list(c.actions)
        for e in l:
            e.update({'proceso': id_proceso})
#        print "get_convocatoria(): actions = ", l
        Action.bulk_insert(l)

        db(Item.proceso==id_proceso).delete()
        l = list(c.items)
        for e in l:
            e.update({'proceso': id_proceso})
#        print "get_convocatoria(): items = ", l
        Item.bulk_insert(l)

        db.commit()
        return True

class SeaceConvocatoria:
    def __init__(self, pages=None):
        self.num_convocatoria = None
        if not pages:
            return None
        if not pages[0]:
            return None
        self.parse(pages.pop(0))
        while pages:
            self.parse_items(pages.pop(0))

    def parse(self, page): 
        match = re.findall('lpnconvocacepto" value="(\d+)', page, flags=re.S)
        if not match:
            self.num_convocatoria = None
            return False
        self.num_convocatoria = match[0]

        match = re.findall('<u><b>Convocatoria.*?<br>.*?(<b>.+?</b>).*?<hr>', page, flags=re.S)
        self.nombre = BeautifulSoup(match[0]).find('b').get_text(' ', strip=True) if match else None

        match = re.findall('Entidad Contratante</u><br></b>(.+?)<br>', page, flags=re.S)
        self.entidad = match[0].strip() if match else None

        match = re.findall('Direcci&oacute;n</b></u><br>\s*?(.+?)<br>', page, flags=re.S)
        self.direccion = match[0].strip() if match else None

        match = re.findall('ntesis</b></u><br>\s*?(.+?)<br>', page, flags=re.S)
        self.sintesis = match[0].strip() if match else None

        match = re.findall('Objeto</b></u><br>\s*?(.+?)<br>', page, flags=re.S)
        self.objeto = match[0].strip() if match else None

        match = re.findall('Valor Referencial</b></u><br>(Soles|Dolares|Euros).+?:\s+?([\d\.,]+)', page, flags=re.S)
        if match:
            self.moneda = {'Soles':'PEN', 'Dolares':'USD', 'Euros':'EUR'}.get(match[0][0])
            self.monto = float(match[0][1].strip().replace(',',''))
        else:
            self.moneda = None
            self.monto = None

        match = re.findall('&Uacute;LTIMA ETAPA\s*?: \s*?(.+?)\s*?</b>', page, flags=re.S)
        self.ultima_etapa = match[0].strip() if match else None

#        match = re.findall('(<th>Otras Acciones.+?</table>)', page, flags=re.S)
#        self.acciones = BeautifulSoup(match[0]).get_text(' ', strip=True)
        self.parse_actions(page)        
        self.items_text = ""
        self.items = []
        self.parse_items(page)
        self.parse_calendar(page)
        p = BeautifulSoup(page)
        while p.style:
            p.style.extract()
        while p.script:
            p.script.extract()
        self.html_text = unicode(p)
        return True
 
    def parse_actions(self, page):
        match = re.findall('<th>Otras Acciones de la Convocatoria(.*?)</table>', page, flags=re.S)
        if not match:
            return None
        self.action_html = match[0]
        rows = BeautifulSoup(match[0]).find_all('td')
        self.actions = []
        self.last_action = ''
        self.last_action_on = None
        n = 0
        while rows:
            n += 1
            row = rows.pop(0)
            if row.span:
                row.span.extract()
            a = row.u.extract().get_text() if row.u else None
            row_text = row.get_text(' ', strip=True)
            row_text = re.sub('informado el d.a', '', row_text)
            row_text = re.sub(r'el (\d+/\d+/\d+) a las (\d+:\d+)', r'\1 \2', row_text)
            match = re.findall('(.*?)(\d+/\d+/\d\d\d\d \d+:\d+)(.*)', row_text, flags=re.S)
            if match:
                try:
                    d = datetime.datetime.strptime(match[0][1], '%d/%m/%Y %H:%M')
                except ValueError:
                    d = None
                t = (match[0][0].strip(' ,') + ' ' + match[0][2].strip(' ,')).strip()
                if not self.last_action_on or d > self.last_action_on:
                    self.last_action_on = d
                    self.last_action = a + " " + t
                self.actions.append(dict(action_number=n, action_date=d, action_name=a, action_text=t))
            else:
                match = re.findall('(NOTIFICACI.N ELECTR.NICA) (.*)', row_text)
                if match:
                    d = None
                    try:
#                        print "parse_actions(): row.a['onclick'] =", row.a['onclick'], "type", type(row.a['onclick'])
#                        print "parse_actions(): entering match"
                        m = re.search('(\d+).+?(\d+)', row.a['onclick'])
#                        print "parse_actions(): after match"
#                        print "Found notificacion with", m.group(1), "and", m.group(2)
                        uri = SEACE.build_notificacion_uri(m.group(1), m.group(2))
#                        print "parse_actions(): get uri", uri
                        doc = SEACE.get_page(uri)
                        if doc:
                            ds = re.search('(\d+/\d+/\d+ \d+:\d+)', doc)
#                            print "parse_actions(): matched", ds.group(1)
                            if ds:
                                d = datetime.datetime.strptime(ds.group(1), '%d/%m/%Y %H:%M')
                    except:
                        pass
                    a = match[0][0]
                    t = match[0][1]
                    if not self.last_action_on or d > self.last_action_on:
                        self.last_action_on = d
                        self.last_action = a + " " + t
                    self.actions.append(dict(action_number=n, action_date=d, action_name=a, action_text=t))
                else:
                    self.actions.append(dict(action_number=n, action_date=None, action_name=a, action_text=row_text))
#        print self.actions

    def parse_items(self, page):
        match = re.findall('</table>(<table.+?<th>Item.+?</table>)', page, flags=re.S)
        if not match:
            return None
        rows = BeautifulSoup(match[0]).find_all('tr')
        rows.pop(0) # first header row
        rows.pop(0) # second header row
        i = ""
        while rows:
            data = rows.pop(0).find_all('td')
            item_number = int(data[0].get_text(strip=True))
            item_description = data[1].get_text(' ', strip=True)
            item_catalog_family = data[2].get_text(' ', strip=True)
            item_quantity = float(data[3].get_text(strip=True).replace(',',''))
            item_uom = data[4].get_text(' ', strip=True)
            try:
                item_unit_price = float(data[5].get_text(strip=True).replace(',',''))
            except:
                item_unit_price = None
            i += item_description + " " + item_catalog_family + "\n"
            self.items.append(dict(item_number=item_number, item_description=item_description,
                item_catalog_family=item_catalog_family, item_quantity=item_quantity,
                item_uom=item_uom, item_unit_price=item_unit_price))
            if rows: # sometimes item tables don't have a hanging last row
                rows.pop(0) # every second row is useless
#        print items
        self.items_text += i

    def parse_calendar(self, page):
#        print "Parsing calendar...",
        self.events = []
        match = re.findall('colspan=3>Calendario\s+(.+?)</table>', page, flags=re.S)
        if not match:
#            print "not found."
            return False
        rows = BeautifulSoup(match[0]).find_all('tr')
        headers = rows.pop(0).find_all('th')
        headers.pop(0) # no use for 1st column 1st row.
        for r in rows:
            rowdata = r.find_all('td')
            tipo = rowdata.pop(0).string # 1st column of row contains event type
            for h in headers:
                hito = re.sub("Fecha ", "", h.string)
                match = re.search('(?P<fecha>\d+/\d+/\d+ \d+:\d+)', rowdata.pop(0).string)
                fecha = datetime.datetime.strptime(match.group('fecha'), "%d/%m/%Y %H:%M") if match else None
                self.events.append(dict(tipo=tipo, hito=hito, fecha=fecha))
        return True
