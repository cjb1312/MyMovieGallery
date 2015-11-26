import os
import json
import math
import time
import sys, io
import shutil
import requests

#templates:
import re
from UserDict import UserDict
from urlparse import urlparse
try:
    from html import escape  # python 3.x
except ImportError:
    from cgi import escape  # python 2.x

# -------------------------------------{O}-------------------------------------#

# Program: My Movie Gallery.
# Author: Gabriel A. Zorrilla. gabriel at zorrilla dot me
# Copyright: GPL 3.0

# -------------------------------------{O}-------------------------------------#

# --------------------------CONFIGURATION PARAMETERS---------------------------#
configfile="config.py";
if not os.path.isfile(configfile) and not os.path.isfile(configfile+".template"):
	print('Missing template or config file: config.py')
	sys.exit()
		  
if not os.path.isfile(configfile):
	copyfile(configfile+".template", configfile);
	print('Just created an config file with defaut values, which may not be suitable for you!!');	
	
if not os.path.isfile(configfile):
	print('Failed to create an config file !')
	sys.exit()

execfile(configfile);

#-------------------------------------{O}-------------------------------------#

"""
    [ string plotoutline = "" ]
    [ string sorttitle = "" ]
    Library.Id movieid
    [ Video.Cast cast ]
    [ string votes = "" ]
    [ Array.String showlink ]
    [ integer top250 = 0 ]
    [ string trailer = "" ]
    [ integer year = 0 ]
    [ Array.String country ]
    [ Array.String studio ]
    [ string set = "" ]
    [ Array.String genre ]
    [ string mpaa = "" ]
    [ Library.Id setid = -1 ]
    [ number rating = 0 ]
    [ Array.String tag ]
    [ string tagline = "" ]
    [ Array.String writer ]
    [ string originaltitle = "" ]
    [ string imdbnumber = "" ] 
"""

def get_movies_from_kodi(host, port):
    url = 'http://' + host + ':' + port + '/jsonrpc'
    headers = {'content-type': 'application/json'}
   
    #we will always limit the search result, maybe some browsers will demand a lower settings
    if limit <= 0:
	maxlimit=1000
    else:
	maxlimit=limit
	
    payload = ({"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", 
         "params": {
    		    "limits":      { "start" : 0, "end": maxlimit },
             "properties":  ["rating", "imdbnumber", "playcount", "plot", "plotoutline", 
				"votes", "top250", "trailer", "year", "country", "studio", 
				"set", "genre", "mpaa", "tag", "tagline", "writer", 
				"originaltitle" ],  
             "sort":        {"order": "ascending", "method": "label", "ignorearticle": True}},
         "id": "libMovies"
       })
                
    try:
        r = requests.post(url, data=json.dumps(payload), headers=headers)
        r = r.json()
        return r['result']['movies']
    except:
        print('Connection error. Please check host and port.')
        sys.exit()


def get_poster_image_url(imdbid, tmdb_key, size, language):
    base_url = 'http://api.themoviedb.org/3/movie/'
    headers = {'content-type': 'application/json'}

    if len(language)<=0: 
	url = requests.get(base_url + imdbid + '/images' + '?api_key=' + tmdb_key +
           '&language=' + lang)
    else:
	url = (base_url + imdbid + '/images' + '?api_key=' + tmdb_key +
           '&language=' + language[0])

    r = requests.get(url)
    i = 0
    try:
	# we want aspec ratio 0.66667 but this way we are a bit more flexible, maybe look at the vote count aswell
        while r.json()['posters'][i]['aspect_ratio'] > 0.67 or r.json()['posters'][i]['aspect_ratio'] < 0.6:
            i += 1
        image_url = r.json()['posters'][i]['file_path']
        poster_url = 'http://image.tmdb.org/t/p/' + size + image_url
    except LookupError:
	if len(language)>=2:
		#remove first element, and call recursive
		language.pop(0)
		poster_url = get_poster_image_url(imdbid, tmdb_key, size, language)
	else:
        	print('No poster exists. Using default no poster image. '+ url ) 
        	poster_url = "no-image"

    return poster_url


def check_if_poster_exists(imdbid, size, web_dir):
    folder_path = os.path.join(web_dir, 'posters', size)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    if os.path.isfile(os.path.join(folder_path, imdbid + '.jpeg')):
        return True


def save_poster_image(poster_url, imdbid, size, web_dir):
    folder_path = os.path.join(web_dir, 'posters', size)

    if poster_url == 'no-image':
        no_image_path = os.path.join(web_dir, 'assets',
                                     'no-image-' + size + '.jpeg')
        filepath = os.path.join(folder_path, imdbid + '.jpeg')
        copyfile(no_image_path, filepath)
    else:
        r = requests.get(poster_url)
        filetype = r.headers['content-type'].split('/')[-1]
        filepath = os.path.join(folder_path, imdbid + '.' + filetype)
        f = open(filepath, "wb")
        f.write(r.content)
        f.close()


def movie_stars(stars=0,votes=0):
    full_stars = int(math.floor(round(stars) / 2))
    remaining_stars = round(stars) / 2 - full_stars;
    full_star_url = os.path.join('assets', 'star-full.svg')
    half_star_url = os.path.join('assets', 'star-half.svg')
    img_full_star_html = "<img src='" + full_star_url + "' alt='star full' title='"+str(round(stars,1))+" rating with "+str(votes)+" votes'>"
    img_half_star_html = "<img src='" + half_star_url + "' alt='star half' title='"+str(round(stars,1))+" rating with "+str(votes)+" votes'>"
    if remaining_stars >= 0.5:
        html_stars = img_full_star_html * full_stars + img_half_star_html
    else:
        html_stars = img_full_star_html * full_stars
    return html_stars


##########################################################################################################################
#extend the userdict for textreplace (replace tekst with a dict of key=value pairs)
class tekstreplace(UserDict):
	def _make_regex(self):
		return re.compile("(%s)" % "|".join(map(re.escape, self.keys())))

	def __call__(self, mo):
		# Count substitutions
		self.count += 1 # Look-up string
		return self[mo.string[mo.start():mo.end()]]

	def substitute (self, text):
		# Reset substitution counter
		self.count = 0
		# Process text
		return self._make_regex().sub(self, text)
	
	#make keys out of the dict, keys are surrounded by % and the values are escaped
	#arrays will become  , seperated stings
	def dict2keys(self, _keys):
		keys={}
		for k,v in _keys.iteritems():
			if str(k)[0] is not '\%':
				if isinstance(v, (list, tuple)):
					keys["%%%s%%"%(k)]=escape(', '.join(v))
				elif isinstance(v, (int, long, float, complex)):
					keys["%%%s%%"%(k)]=unicode(v)
				elif isinstance(v, basestring):
					keys["%%%s%%"%(k)]=escape(unicode(v))
				else:
					keys["%%%s%%"%(k)]=unicode(v)
			else:
				keys[k]=v
		return keys

def gettrailer(params):
	try:
		murl=urlparse(params['trailer'])
		if 'youtube' in murl.netloc:
			for param in murl.query.split('&') : 
				paramlist=param.split('=')
				if paramlist[0]=='videoid':
					return 'http://www.youtube.com/watch?v='+paramlist[1]

	except:
		print "no youtube trailer info found.."
		
	return ""

def create_movie_html_block(params):

	row_open = ''
	row_close = ''

	if 'votes' not in params:
		params['votes']=0
	if 'rating' not in params:
		params['rating']=0


	keys=tekstreplace().dict2keys(params)
	keys['watchedclass'] = 'unwatched'
	
	if params['playcount'] > 0 :
		keys['watchedclass'] = 'watched'
      	
	if params['counter'] == 1:
		row_open = '<tr>'
		row_close = ''
	elif params['counter'] == 5:
		row_open = ''
		row_close = '</tr>'
      

	keys['%trailerurl%']=gettrailer(params)
	keys['%trailerhtml%'] = ''
	if len(keys['%trailerurl%']) > 0:
		keys['%trailerhtml%'] = tekstreplace(keys).substitute(trailer_template)
	keys['%starshtml%']=movie_stars(params['rating'],keys['%votes%'])
	
	return    unicode(tekstreplace(keys).substitute(movie_template) )




def write_html(movies, web_dir):
	
	if cssinline and os.path.exists(cssfile):
	 	with open(cssfile) as f:
	 		css_data ="<STYLE>\n"+f.read()+"</STYLE>" 
    		f.close()
	else:
		css_data=cssfile_template

	keys={
      '%NAME%': gallery_name,
      '%META%': meta_template,
      '%MADEBY%': made_template,
      '%PROJECTURL%': projectLink_template,
      '%TMDBLOGO%': tmdblogo_template,
      '%CSSFILE%': css_data,
      '%MOVIE_HTML%': movies,
      '%CREATED%': time.strftime("%Y.%m.%d@%H:%M:%S")
	}
       
	f = io.open(os.path.join(web_dir, 'index.html'), 'w', encoding='utf-8')
	f.write(unicode(tekstreplace(keys).substitute(html_template) ))
	f.close()


def pushbullet_notification(apikey, movies, gallery, device):
    string_to_push = ''
    for i in movies:
        string_to_push += i + ', ' 
    string_to_push = 'New movies added: ' + string_to_push[:-2] + '.'
    url = 'https://api.pushbullet.com/v2/pushes'
    headers = {'content-type': 'application/json',
               'Authorization': 'Bearer ' + apikey}
    payload = {'device_iden': device, 'type': 'note', 'title': gallery,
               'body': string_to_push}
    requests.post(url, data=json.dumps(payload), headers=headers)


if __name__ == "__main__":
    posters_to_retrieve = []
    label_posters_to_retrieve = []
    movies_html = ""
    counter = 1

    if htmllint:
    	import tempfile
	from tidylib import tidy_document

	out_dir=tempfile.mkdtemp()
	print "htmllint enabled: building in:"+out_dir 

    else:
    	out_dir=web_dir


    for i in get_movies_from_kodi(host, port):
        r = check_if_poster_exists(i['imdbnumber'], poster_size, out_dir)
        poster_url = ("posters/" + poster_size + "/" + i['imdbnumber'] +
                      '.jpeg')
        
        i['poster_url']=poster_url;
        i['counter']=counter;
        
        movies_html = (movies_html + create_movie_html_block(i))
        
        if not r or refreshposters:
            posters_to_retrieve.append(i['imdbnumber'])
            label_posters_to_retrieve.append(i['label'])
        if counter != 5:
            counter += 1
        else:
            counter = 1
    posters_to_get = str(len(posters_to_retrieve))
    counter = 0
    for i in posters_to_retrieve:
        counter += 1
        url = get_poster_image_url(i, tmdb_key, poster_size, language)

        save_poster_image(url, i, poster_size, out_dir)
        print('Downloaded poster ' + str(counter) + ' / ' + posters_to_get +
              '.')
    write_html(movies_html, out_dir)
    if pushbullet_api_key != '':
        if len(label_posters_to_retrieve) != 0:
            pushbullet_notification(pushbullet_api_key,
                                    label_posters_to_retrieve, gallery_name,
                                    pushbullet_device_iden)


    if htmllint:
    	with open(os.path.join(out_dir, 'index.html')) as f:
    		document, errors = tidy_document(f.read(),options={'numeric-entities':1, "show-warnings": False})
    		f.close()
    		if len(errors) > 0:
			print "we got some errors and will not release:"
			print error
    		else:
			print "release result to website: "+web_dir 
			if web_dir=='':
    				web_dir=os.getcwd()
			shutil.move(out_dir+"/*",web_dir )
    	



