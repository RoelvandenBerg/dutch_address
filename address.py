# -*- coding: UTF-8 -*-
'''
Created on 9 jan. 2015

@author: Roel van den Berg

header postcode_NL.csv:
0      id               395614
1      postcode         7940XX
2      postcode_id      79408888
3      pnum             7940
4      pchar            XX
5      minnumber        4
6      maxnumber        12
7      numbertype       mixed
8      street           Troelstraplein
9      city             Meppel
10     city_id          1082
11     municipality     Meppel
12     municipality_id  119
13     province         Drenthe
14     province_code    DR
15     lat              52.7047653217626
16     lon              6.1977201775604
17     rd_x             209781.52077777777777777778
18     rd_y             524458.25733333333333333333
19     location_detail  postcode
20     changed_date     2014-04-10 13:20:28

Thus:
min = 5
max = 6
type = 7
x = 17
y = 18
street = 8
city = 9
postal_code = 1
'''

from FileHandler import load
import unicodedata
import re
import pickle

def smallest_dist(h, *housenumbers):
    minmax = {x:min(abs(x.min-h), abs(x.max-h)) for x in housenumbers}
    return min(minmax, key=minmax.get)

def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

dirlist = load.dirlist()


def even(val):
    if (val % 2 == 0):
        return "EVEN"
    else:
        return "ODD"


def infmax(l):
    try:
        return max(l)
    except ValueError:
        return float('inf')


class AddressTypeError(Exception):
    pass


class Address(object):
    
    def __init__(self, city=None, street=None, houseno=0, x=0, y=0, address_string=None):
        self.city = city
        self.street = street
        self.housenumber = houseno
        self.x = x
        self.y = y
        self.address_string = address_string

    def __str__(self):
        return " ".join([self.city, self.street, str(self.housenumber), 'x = %s, y = %s' %(str(self.x), str(self.y))])


class PostalCode(object):
    
    def __init__(self):
        addressfile = [[strip_accents(x.strip('"')) for x in y] for y in load.csv(dirlist["data"] + r"\postcode_NL.csv")]
        all_codes = set([(line[1], line[9], line[8]) for line in addressfile])
        self.codes = {postal_code: (city, street) for postal_code, city, street in all_codes}


class HouseNumber(object):
    
    def __init__(self, min_housen, max_housen, numbertype, x, y):
        self.min = min_housen
        self.max = max_housen
        self.type = numbertype
        self.x = x
        self.y = y

    def match(self, housen):
        if self.type != "MIXED" and self.type != even(housen):
            return 0
            #raise AddressTypeError("Self type: '%s' does not match other: '%s'" %(self.type, even(housen)))
        if self.min <= housen <= self.max:
            return 0
        elif housen < self.min:
            return -1
        elif housen > self.max:
            return 1
        else:
            raise AddressTypeError("You found a bug in the address.match module")    

    def match_even_type(self, x):
        return even(x) == self.type or self.type == "MIXED"

class Street(object):
    
    def __init__(self, name):
        self.name = name
        self.housenumbers = []
        self.min = float('inf')
        self.max = 0
        self.len = 0
        self.type = None
   
    def add(self, housenumber):
        self.housenumbers.append(housenumber)
        self.housenumbers.sort(key=lambda x: x.min)
        self.min = self.housenumbers[0].min
        self.max = max([self.max, housenumber.max])  
        self.len += 1
        
        if not self.type:
            self.type = housenumber.type
        elif self.type != housenumber.type:
            self.type = "multi"
    
    def find(self, housen=0):
        if housen == 0:
            housenumber = self.housenumbers[int(self.len/2)]
            return housenumber.x, housenumber.y
        elif self.type == "multi":
            housenumbers = [x for x in self.housenumbers if x.type == "MIXED" or x.type == even(housen)]
            length = len(housenumbers)
            return self.find_RD_coord(housen, housenumbers, length)
        else:
            return self.find_RD_coord(housen, self.housenumbers, self.len)        
  
    def find_RD_coord(self, housen, housenumbers, length):
        halfway = int(length/2)
        match = housenumbers[halfway].match(housen)
        try:
            if match == 0:
                return housenumbers[halfway].x, housenumbers[halfway].y
            elif len(housenumbers) == 1:
                h = housenumbers[0]
                housenos = [x for x in self.housenumbers if x.match_even_type(housen)]
                i = housenos.index(h)
                try:
                    fit = smallest_dist(housen, h, housenos[i-1], housenos[i+1])
                except IndexError:
                    try: 
                        fit = smallest_dist(housen, h, housenos[i-1])
                    except IndexError:
                        fit = smallest_dist(housen, h)
                print('Bij straat: "%s", is bij het gezochte huisnr %d de dichtsbijzijnde range: %d-%d uit het adresboek.' %(self.name, housen, fit.min, fit.max))
                return fit.x, fit.y
            elif match == 1:
                return self.find_RD_coord(housen, housenumbers[halfway:], length - halfway)
            else:
                return self.find_RD_coord(housen, housenumbers[:halfway], halfway)
        except RuntimeError:
            print(housen, ["-".join([str(x.min), str(x.max)]) for x in  housenumbers], ["-".join([str(x.min), str(x.max)]) for x in self.housenumbers], length)
            exit()
            

class City(object):
    
    def __init__(self, name):
        self.name = name
        self.streets = {}

    def find(self, street, housen=0):
        return self.streets[street].find(housen)
   
    def add(self, street, housenumber):
        try:
            self.streets[street].add(housenumber)
        except KeyError:
            new_street = Street(street)
            new_street.add(housenumber)
            self.streets[street] = new_street


class AddressBook(object):
    
    def __init__(self):
        with open(dirlist["data"] + r"\plaatsnamen_schrijfwijze.csv", 'r') as f:
            bestandsinhoud = [[strip_accents(y.upper().strip('\n')) for y in x.split(';')] for x in f.readlines()]
        self.alternate_cities = {y:x[0] for x in bestandsinhoud for y in x[1:]}
#        self.alternate_cities = {z[0].upper():tuple([a.upper() for a in z[1:]]) for x in bestandsinhoud for z in permutations(x)}
        self.cities = {}
        self.postal_code = PostalCode()
    
    def load(self):
        addressfile = [[strip_accents(x.strip('"')) for x in y] for y in load.csv(dirlist["data"] + r"\postcode_NL.csv")]
        for line in addressfile:
            min_housen, max_housen, addresstype, street, city, x, y = [int(x) for x in line[5:7]] + [x.upper() for x in line[7:10]] + [float(x) for x in line[17:19]]
            new_address = HouseNumber(min_housen, max_housen, addresstype, x, y)
            self.add(city, street, new_address)
    
    def add(self, city, street, housenumber):
        try:
            self.cities[city].add(street, housenumber)
        except KeyError:
            new_city = City(city)
            new_city.add(street, housenumber)
            self.cities[city] = new_city

    def find(self, city, street, housen=0):
        print("Zoek RD-coördinaten voor: %s, %s, %s" %(city, street, str(housen)))
        try:
            return self.cities[city.upper()].find(street.upper(), int(housen))
        except KeyError:
            for alternate_city in self.alternate_cities[city.upper()]:
                print("%s niet gevonden in adresboek, probeer nu alternatief: %s" %(city, alternate_city))
                try:
                    return self.cities[alternate_city].find(street.upper(), int(housen))
                except KeyError:
                    print('"%s" heeft geen resultaat opgeleverd.' % alternate_city)
                    
    def find_PC(self, PC):
        city, street = self.postal_code[PC]
        return self.find(city, street)


class AddressSearch(object): 
    
    def __init__(self, address_string, address_book=None):
        self.error_log = []
        if not address_book:
            self.address_book = AddressBook()
            self.address_book.load()
        else:
            self.address_book = address_book
        self.address_string = address_string.upper()
        self.cities = list(self.address_book.cities.keys())
        self.alternate_cities =  list(self.address_book.alternate_cities.keys())
        self.x, self.y = [], []
        self.city, self.street, self.housenumber = [], [], []
        self.addresses = []

    def find_RD_coord(self, NA="NA"):
        try:
            for i in range(len(self.housenumber)):
                x, y = self.address_book.find(self.city[i], self.street[i], self.housenumber[i])            
                self.x.append(x)
                self.y.append(y)
            self.addresses = [Address(city, self.street[i], self.housenumber[i], self.x[i], self.y[i], self.address_string) for i, city in enumerate(self.city)]
        except KeyError:
            self.reset()
            self.addresses = [Address(NA, NA, NA, NA, NA, self.address_string)]
            
    def reset(self):
        self.x, self.y = [], []
        self.city, self.street, self.housenumber = [], [], []
        self.addresses = []

    def find(self, address_string = None):
        if address_string:
            self.reset()
            self.address_string = address_string.upper()     
        possible_cities = [city for city in self.cities if self.re_test(city)]
        possible_cities = [city if not city in self.alternate_cities else self.address_book.alternate_cities[city] for city in possible_cities]
        if len(possible_cities) == 0:
            self.find_RD_coord()
        if len(possible_cities) == 1:
            city = possible_cities[0]
            streets = self.address_book.cities[city].streets.keys()
            city_street = list(set([(city, street) for street in streets if self.re_test(street)]))
        else:
            city_street = list(set([(city, street) for city in possible_cities for street in self.address_book.cities[city].streets.keys() if self.re_test(street)]))
        if len(city_street) != 1:
            city_street = list(set([(city, street[0]) for city in possible_cities for street in self.streets(city) if self.re_test(street[1])])) 
        return self.find_city_street(city_street)

    def re_test(self, item):
        return re.compile("(?<=[\s\\/,;\(\)])" + item + "(?=[\s\\/,;\(\)])").search('\n' + self.address_string + '\n')

    def find_city_street(self, city_street):
        if len(city_street) == 1 :
            self.city = [city_street[0][0]]
            self.street = [city_street[0][1]]
            self.housenumber = [self.find_houseno()]
            self.find_RD_coord()
            return self.city, self.street, self.housenumber
        elif len(city_street) > 1:
            return self.multiple_hits(city_street)
        else:
            self.error_log.append(('%d stad - straat combinaties gevonden: %s in PRIO-code: "%s"' %(len(city_street), " en ".join([" - ".join(x) for x in city_street]), self.address_string)))
            self.find_RD_coord()

    def streets(self, city):
        streets = self.address_book.cities[city].streets.keys()
        streetchops = [(street, strt) for street in streets for strt in street.split(" ") if (len(strt) > 4 and strt != city) or infmax([len(x) for x in street.split(" ") if x != city]) <= 4]
        chops = [x[1] for x in streetchops]
        single_chops = [chop for chop in streetchops if chops.count(chop[1]) == 1]
        multi_chops = [chop for chop in streetchops if chops.count(chop[1]) > 1]
        return list(set(single_chops + [part for street, chop in multi_chops for part in ((street, street.split(chop)[0] + chop), (street, chop + street.split(chop)[1])) if part[1] != chop]))     
        
    def find_houseno(self, i=0):
        reg_ex = re.compile(r'(?<=' + self.street[i] + '\s)\d+') #r'(?<=%s\s)\d+[A-Z]+'
        houseno = reg_ex.findall(self.address_string)
        if len(houseno) > 1:
            self.error_log.append('Meerdere huisnrs gevonden: %s in %s - %s in PRIO-code: "%s"' %(", ".join(list(houseno)), self.city[i], self.street[i], self.address_string))#raise CityError('Meerdere huisnrs gevonden: %s in %s - %s in PRIO-code: "%s"' %(", ".join(list(houseno)), self.city, self.street, self.address_string))
        if len(houseno) == 0:
            return 0
        return int(houseno[0])

    def multiple_hits(self, city_street):
        cities = set([city for city, _ in city_street])
        if len(cities) > 1:
            self.error_log.append('Meerdere steden gevonden: %s. voor: %s' % (", ".join(list(cities)), self.address_string))
        streets = [street for _, street in city_street]
        compare = [x for x in streets for y in streets if (y in x and not x in y) or (not y in x and not x in y)]
        streets = set([x for x in compare if compare.count(x) == max([compare.count(x) for x in compare])])
        streets = [x for x in streets if re.compile(r'\s' + x + r'[\s$]').search(self.address_string)]
        city_street = [(city, street) for city, street in city_street if street in streets]
        if len(city_street) > 1:
            self.city = [city for city, _ in city_street]
            self.street = [street for _, street in city_street]
            self.housenumber = [self.find_houseno(i) for i in range(len(city_street))]
            return self.city, self.street, self.housenumber
        else:
            return self.find_city_street(city_street)

    def __str__(self):
        return '\n'.join([str(x) for x in self.addresses])


if __name__ == "__main__":
    print('Adressenbestand laden...')
    adressenbestand = pickle.load(open(dirlist["data"] + r"\adressenbestand.p", 'rb'))
    print('Adressenbestand geladen.')
    search_string = ""
    search_item = AddressSearch(search_string, adressenbestand)
    search_item.find()
    print(search_item)
    search_string_2 = ""
    search_item.find(search_string_2)
    print(search_item)