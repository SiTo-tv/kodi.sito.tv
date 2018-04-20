# -*- coding: utf-8 -*-
import copy
import datetime
import json
import os
import urllib
import urllib2


# noinspection PyUnusedLocal
def log(txt, level=0):
    # debug output, replaced in the addon.py
    print 'bitx: %s' % (str(txt).encode('ascii', 'ignore'))


# noinspection PyUnusedLocal,PyShadowingNames
def url_for(endpoint, **items):
    return "%s?%s" % (endpoint, items)


def is_android():
    try:
        return 'XBMC_ANDROID_APK' in os.environ.data
    except Exception as e:
        log("is_android error: %s" % e, level=4)
        return False


def image_resource_url(image_resource):
    return image_resource


SITO_FANART_IMAGE = image_resource_url('fanart.jpg')
SITO_CATEGORY_ICON = 'resources/media/icon_%s.png'

PLUGIN_ID = 'kodi.sito.tv'

notice = log
store = {}
requests_cache = {}

NONE = '-'

REQUESTS_TIMEOUT = 600
TORRENT_FILES_LOOKUP = True
LOCAL_TEST_MODE = False

PREV_NEXT_COLOR = 'FF4FC3F7'  # Simple yellow
ADDITIONS_COLOR = 'FF9E9E9E'  # Grey

genres_list = [
    'Action',
    'Adventure',
    'Animation',
    'Biography',
    'Comedy',
    'Crime',
    'Documentary',
    'Drama',
    'Family',
    'Fantasy',
    'Film-Noir',
    'Game-Show',
    'History',
    'Horror',
    'Music',
    'Musical',
    'Mystery',
    'News',
    'Reality-TV',
    'Romance',
    'Sci-Fi',
    'Short',
    'Sport',
    'Talk-Show',
    'Thriller',
    'War',
    'Western'
]

USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.101 Safari/537.36'

DEFAULT_API_URL = 'http://vm160.siriomedia.com'

NOTHING_FOUND_PATH = 'Action(ParentDir)'


# noinspection PyDefaultArgument, PyShadowingNames
def api(action, params={}, url='', timeout=REQUESTS_TIMEOUT, method="get"):
    method = "post" if method == "post" else "get"
    params = urllib.urlencode(params)
    url = "%s/%s" % (url.rstrip('/') or DEFAULT_API_URL.rstrip('/')+'/v1', action)
    log("api) url = %s?%s" % (url, params))
    try:
        is_get = method == "get"
        if is_get:
            # log("GET REQUEST")
            url = "%s?%s" % (url, params)
            cached = requests_cache.get(url)
            if cached:
                log('api) --> using cached response')
                return cached

            request = urllib2.Request(url)
            # response = urllib2.urlopen(url, timeout=timeout)
        else:
            # log("POST REQUEST")
            request = urllib2.Request(url, data=params)

        # request.add_header('Authorization', 'Bearer %s' % __settings__.getSetting('access_token'))
        response = urllib2.urlopen(request, timeout=timeout)
        data = json.loads(response.read())

        if is_get and data:
            requests_cache[url] = data

        return data

    except urllib2.HTTPError as e:
        # noinspection PyBroadException
        try:
            data = json.loads(e.read())
        except:
            data = {'success': False, 'err': ['Unknown server error']}

        error = (data and (data.get('err') or data.get('error'))) or 'Unknown server error'
        log("API error: %s // %s\n %s" % (error, url, e), level=4)
        return data

    except Exception as e:
        log("API error: %s\n %s" % (url, e), level=4)
        return {'success': False, 'err': ["Unknown error: %s" % e]}


def track_view(entry_id, api_data=None, category='movies', timeout=10):
    # Local tracking
    if entry_id and api_data:
        viewed_storage = store.get('viewed')
        if not viewed_storage:
            viewed_storage = {}
            store['viewed'] = viewed_storage

        viewed = viewed_storage.get(category) or []

        i = 0
        while i < len(viewed):
            v_item = viewed[i]
            if not v_item:
                viewed.pop(i)
                continue
            v_id, v_data = v_item
            if v_id == entry_id:
                viewed.pop(i)
                break
            i += 1

        viewed.insert(0, (entry_id, api_data))

        # limit max size of viewed list to 150
        if len(viewed) > 150:
            viewed = viewed[:150]

        viewed_storage[category] = viewed

    # Backend tracking
    imdb_code = api_data.get('imdb_code') or entry_id
    if imdb_code and not LOCAL_TEST_MODE:
        # vm160.siriomedia.com/v1/track/view/movie/tt0085970/
        # vm160.siriomedia.com/v1/track/view/series/tt0085970/
        category_term = 'series' if category == 'tvshows' else 'movie'
        params = urllib.urlencode({'_id': entry_id})
        url = "http://vm160.siriomedia.com/v1/track/view/%s/%s/?%s" % (category_term, imdb_code, params)
        log("track_view) url = %s" % url)
        try:
            if REQUESTS_TIMEOUT < timeout:
                timeout = REQUESTS_TIMEOUT

            request = urllib2.Request(url)
            response = urllib2.urlopen(request, timeout=timeout)
            response.read()
        except Exception as e:
            log("track_view error: %s\n %s" % (url, e), level=4)


def get_server_versions():
    # http://vm160.siriomedia.com/api/version
    response = api('api/version', url=DEFAULT_API_URL)
    data = response.get('data')
    return data


def load_item_by_id(entry_id, category='movies'):
    # vm160.siriomedia.com/v1/movies/tt2239822
    # vm160.siriomedia.com/v1/tvshows/tt1520211
    response = api(category+'/'+entry_id)
    data = response.get('data')
    return data


# == Lists creation ==

# noinspection PyShadowingNames
def create_kodi_last_viewed_list(category='movies'):
    items = []
    viewed_storage = store.get('viewed')
    if viewed_storage:
        viewed = viewed_storage.get(category)
        if viewed:
            if category == "tvshows":
                items = [make_tvshow_item(entry) for entry_id, entry in viewed if entry]
            else:
                items = [make_movie_item(entry) for entry_id, entry in viewed if entry]

    log("last viewed %s items: %s" % (category, len(items)))
    if items:
        return items

    name = 'TV Shows' if category == 'tvshows' else 'Movies'
    return result_error('No recently viewed %s found, view something ;)' % name, category, do_notice=False)


# noinspection PyShadowingNames
def create_kodi_playlists_list(data, page=1, category='movies', search_term=NONE):
    if not data or not data.get('success') or data.get('err'):
        return result_error("Error " + str(next(iter(data.get('err')))), category)

    if category != 'movies' and category != 'tvshows':
        return result_not_supported_category(category)

    has_next_page = data.get('paging') and int(data['paging'].get('total_pages', '0')) > page
    has_prev_page = page > 1

    entries = data['data']['playlists']
    store['store'] = entries

    items = [make_playlist_item(entry, category) for entry in entries if entry]

    if has_next_page:
        new_page = str(page + 1)
        next_item = {
            'label': '[COLOR %s][B]next (%s) >>[/B][/COLOR]' % (PREV_NEXT_COLOR, new_page),
            'path': url_for('make_playlist_item', category=category, page=new_page, search_term=search_term)
        }
        items.insert(0, next_item)
        items.insert(len(items), next_item)

    if has_prev_page:
        new_page = str(page - 1)
        items.insert(0, {
            'label': '[COLOR %s][B]<< previous (%s)[/B][/COLOR]' % (PREV_NEXT_COLOR, new_page),
            'path': url_for('action_category_media_page', category=category, page=new_page, search_term=search_term)
        })

    if not items:
        name = 'TV Shows' if category == 'tvshows' else 'Movies'
        return result_nothing_found('%s Collections' % name)

    return items


# noinspection PyShadowingNames
def create_kodi_playlist_list(playlist_id, category='movies'):
    items = []

    playlist_data = _get_playlist_data(playlist_id)
    if playlist_data:
        entries = playlist_data.get('items')
        if entries:
            if category == "tvshows":
                items = [make_tvshow_item(entry) for entry in entries if entry]
            else:
                items = [make_movie_item(entry) for entry in entries if entry]

    return items or result_nothing_found(category)


# noinspection PyShadowingNames
def create_kodi_list(data, page=1, category='movies', genre=NONE, search_term=NONE):
    if not data or not data.get('success') or data.get('err'):
        return result_error("Error " + str(next(iter(data.get('err')))), category)

    if category != 'movies' and category != 'tvshows':
        return result_not_supported_category(category)

    has_next_page = data.get('paging') and int(data['paging'].get('total_pages', '0')) > page
    has_prev_page = page > 1

    entries = data['data'][category]
    if category == "tvshows":
        items = [make_tvshow_item(entry) for entry in entries if entry]
    else:
        items = [make_movie_item(entry) for entry in entries if entry]

    store['store'] = entries

    if not items:
        return result_nothing_found(category)

    if has_next_page:
        new_page = str(page + 1)
        next_item = {
            'label': '[COLOR %s][B]next (%s) >>[/B][/COLOR]' % (PREV_NEXT_COLOR, new_page),
            'path': url_for('action_category_media_page', category=category, genre=genre, page=new_page, search_term=search_term)
        }
        items.insert(0, next_item)
        items.insert(len(items), next_item)

    if has_prev_page:
        new_page = str(page - 1)
        items.insert(0, {
            'label': '[COLOR %s][B]<< previous (%s)[/B][/COLOR]' % (PREV_NEXT_COLOR, new_page),
            'path': url_for('action_category_media_page', category=category, genre=genre, page=new_page, search_term=search_term)
        })

    return items


# == Internal helpers ==

def create_kodi_tvshow_seasons_list(_id):
    items = []

    show = _get_stored_data_for_id(_id, category='tvshows')
    if not show or not show.get('seasons'):
        return result_nothing_found("seasons")

    result_base = make_tvshow_item(show, as_stub=True)
    tvshowtitle = result_base['info']['tvshowtitle']
    for season_key in show['seasons']:
        eposodes = show['seasons'][season_key]
        item = copy.copy(result_base)

        # Get season number
        season_number = 0
        if eposodes:
            for eposode_key in eposodes:
                eposode = eposodes[eposode_key]
                if eposode.get('season'):
                    try:
                        season_number = int(eposode['season'])
                        break
                    except:
                        pass

        if not season_number:
            try:
                season_number = int(season_key[1:])
            except:
                pass

        if season_number:
            item['info']['season'] = season_number

        length = len(eposodes)
        item['label'] = '%s, [B]Season %s[/B]  [COLOR %s](%s %s)[/COLOR]' % (
            tvshowtitle, season_number, ADDITIONS_COLOR, length, 'episode' if length == 1 else 'episodes')
        item['path'] = url_for('action_tvshow_season', entry_id=_id, season=season_key)
        item['__season__'] = season_number
        items.insert(len(items), prepare_list_item(item, 'tvshows', mediatype='season', is_structural=False))

    if len(items) > 1:
        items = sorted(items, key=lambda s: -s['__season__'])

    return items or result_nothing_found("seasons")


def create_kodi_tvshow_episodes_list(_id, season=''):
    items = []

    show = _get_stored_data_for_id(_id, category='tvshows')
    if not show or not show.get('seasons'):
        return result_nothing_found("episodes")

    result_base = make_tvshow_item(show, as_stub=True)
    tvshowtitle = result_base['info']['tvshowtitle']
    for season_key in show['seasons']:
        if not season or season == NONE or season_key == season:
            # Default season number
            try:
                season_number = int(season_key[1:])
            except:
                season_number = 0

            eposodes = show['seasons'][season_key]
            for eposode_key in eposodes:
                episode_data = eposodes[eposode_key]
                item = copy.copy(result_base)

                _season_key = season_key or episode_data.get('season_id')
                _episode_id = eposode_key or episode_data.get('episode_id')
                episode_symbol = episode_data.get('id') or '%s%s' % (_season_key, _episode_id)

                # Get season number
                _season_number = season_number
                if episode_data.get('season'):
                    try:
                        _season_number = int(episode_data['season'])
                    except:
                        pass
                if not _season_number:
                    try:
                        _season_number = int(_season_key[1:])
                    except:
                        pass

                # Get episode number
                _episode_number = 0
                if episode_data.get('episode'):
                    try:
                        _episode_number = int(episode_data['episode'])
                    except:
                        pass
                if not _episode_number:
                    try:
                        _episode_number = int(_episode_id[1:])
                    except:
                        pass

                if _season_number:
                    item['info']['season'] = _season_number

                if _episode_number:
                    item['info']['episode'] = _episode_number

                episode_name = None
                if episode_data.get('episode'):
                    episode_name = '%s, Season %s, [B]Episode %s[/B]  [COLOR %s](%s)[/COLOR]' % (
                        tvshowtitle, _season_number, _episode_number, ADDITIONS_COLOR, episode_symbol)

                item['label'] = episode_name or episode_symbol
                item['path'] = url_for('action_tvshow_episode', entry_id=_id, season=_season_key, episode=_episode_id)
                item['__season__'] = _season_number
                item['__episode__'] = _episode_number
                items.insert(len(items), prepare_list_item(item, 'tvshows', mediatype='episode', is_structural=False))
            if season:
                break

    if len(items) > 1:
        items = sorted(items, key=lambda s: -(s['__season__'] * s['__episode__'] + s['__season__'] + s['__episode__']))

    return items or result_nothing_found("episodes")


def make_movie_item(data, as_stub=False):
    # http://vm160.siriomedia.com/static/images/movies/api.txt
    # http://vm160.siriomedia.com/v1/movies?page=1

    # "_id": "59b80872c80975a42e456a0e",
    # "url": "https://yts.ag/movie/mr-mom-1983",
    # "imdb_code": "tt0085970",
    # "timeadded": 1505233010.0041828,
    # "title": "Mr. Mom",
    # "year": 1983,
    # "ratings": {
    #     "imdb" : 6.8,
    #     "rottentomato": "86/100"
    # },
    # "genres": [
    #     "Comedy",
    #     "Drama"
    # ],
    # "synopsis": null,
    # "description": null,
    # "trailer" : "ld4eE2HU-ig",
    # "language": "English",
    # "mpa_rating": "PG",
    # "background_image": "https://yts.ag/assets/images/movies/mr_mom_1983/background.jpg",
    # "small_cover_image": "https://yts.ag/assets/images/movies/mr_mom_1983/small-cover.jpg",
    # "large_cover_image": "https://yts.ag/assets/images/movies/mr_mom_1983/large-cover.jpg",
    # "magnets": [
    #     {
    #         "link": "magnet:?xt=urn:btih:929197D0C62179CCAEE98139129B3590CC0519B4&dn=Mr.+Mom+1983",
    #         "quality": "720p",
    #         "source": "yts",
    #         "seeds": 288,
    #         "peers": 99,
    #         "size": "649.47 MB",
    #         "size_bytes": 681018655,
    #         "date_created": "",
    #         "timestamp_created": ""
    #     },
    #     {
    #         "link": "magnet:?xt=urn:btih:02EF9AA092BC9E1B087F6A9A09470F695DFEB35B&dn=Mr.+Mom+1983&tr=udp://open.demonii.com:1337/announce",
    #         "quality": "1080p",
    #         "source": "yts",
    #         "seeds": 277,
    #         "peers": 84,
    #         "size": "1.37 GB",
    #         "size_bytes": 1471026299,
    #         "date_created": "",
    #         "timestamp_created": ""
    #     }
    # ]

    # https://github.com/afrase/kodiswift/blob/master/docs/item.rst#the-listitem
    # http://mirrors.kodi.tv/docs/python-docs/16.x-jarvis/xbmcgui.html#ListItem-setInfo

    result = prepare_media_info(data, 'movies', as_stub)
    result['path'] = url_for('action_movie', entry_id=_get_entry_id(result))

    # log(result)
    return result


def make_tvshow_item(data, as_stub=False):
    # http://vm160.siriomedia.com/static/images/movies/api.txt
    # http://vm160.siriomedia.com/v1/tvshows?page=1

    # "_id": "59bb880fc80975a42e458278",
    # "url": null,
    # "imdb_code": "tt1837492",
    # "timeadded": null,
    # "title": "13 Reasons Why",
    # "year": "2017\u2013",
    # "ratings": {
    #   "imdb": "8.5"
    # },
    # "genres": [
    #   "Drama",
    #   " Mystery"
    # ],
    # "synopsis": null,
    # "description": "Thirteen Reasons Why, based on the best-selling books by Jay Asher ...",
    # "language": "English",
    # "mpa_rating": null,
    # "background_image": null,
    # "small_cover_image": null,
    # "large_cover_image": null,
    # "season_count": 1,
    # "seasons": {
    #   "S01": {
    #     "E13": {
    #       "id": "S01E13",
    #       "season": 1,
    #       "episode": 13,
    #       "magnets": [
    #         {
    #           "source": "showrss.info",
    #           "quality": "1080p",
    #           "link": "magnet:?xt=urn:btih:75F7588D80137562522847BE8587F2A00F6889D9&dn=13+Reasons+Why+S01E13+1080p+WEBRip+X264+DEFLATE"
    #         },
    #         {
    #           "source": "showrss.info",
    #           "quality": "720p",
    #           "link": "magnet:?xt=urn:btih:F14881DA2EDAD08A0F9E605F25FB04CB5567EC5F&dn=13+Reasons+Why+S01E13+720p+WEBRip+X264+DEFLATE"
    #         }
    #       ],
    #       "season_id": "S01",
    #       "episode_id": "E13"
    #     },
    #     "E12": {
    #       "id": "S01E12",
    #       "season": 1,
    #       "episode": 12,
    #       "magnets": [
    #         {
    #           "source": "showrss.info",
    #           "quality": "1080p",
    #           "link": "magnet:?xt=urn:btih:F3133D1DE02DB14BA8D465849B3867B118E92112&dn=13+Reasons+Why+S01E12+1080p+WEBRip+X264+DEFLATE"
    #         },
    #         {
    #           "source": "showrss.info",
    #           "quality": "720p",
    #           "link": "magnet:?xt=urn:btih:63051C0EB156064FEE4C0F083F77E78DAE67E10A&dn=13+Reasons+Why+S01E12+720p+WEBRip+X264+DEFLATE"
    #         }
    #       ],
    #       "season_id": "S01",
    #       "episode_id": "E12"
    #     },
    #   }
    # },
    # "actors": [
    #   "Dylan Minnette",
    #   " Katherine Langford",
    #   " Christian Navarro",
    #   " Alisha Boe"
    # ],
    # "content_rating": "TV-MA"
    # }

    # https://github.com/afrase/kodiswift/blob/master/docs/item.rst#the-listitem
    # http://mirrors.kodi.tv/docs/python-docs/16.x-jarvis/xbmcgui.html#ListItem-setInfo

    result = prepare_media_info(data, 'tvshows', as_stub)
    result['path'] = url_for('action_tvshow', entry_id=_get_entry_id(result))

    # log(result)
    return result


def make_playlist_item(data, category):
    # http://vm160.siriomedia.com/v1/series/playlists?page=1

    # "title": "Batman",
    # "desc": "I'm Batman",
    # "created_date": "2017-09-30 02:00:33.031000",
    # "updated_date": "2017-09-30 02:00:33.031000",
    # "ltype": "movie",
    # "tags": Array[2][
    #       "batman",
    #       "im batman"
    #   ],
    # "visible": true,
    # "items": Array[16][
    #     {
    #         "title": "Batman and Harley Quinn",
    #         "year": 2017,
    #         "imdb_code": "tt6556890",
    #         "url": null,
    #         "timeadded": 1508741520.552886,
    #         "ratings": Array[1][
    #             {
    #                 "id": "None"
    #             }
    #         ],
    #         "genres": Array[3][
    #             "Animation",
    #             "Action",
    #             "Adventure"
    #         ],
    #         "synopsis": null,
    #         "description": "Batman and Nightwing are forced to team with the Joker's sometimes-girlfriend Harley Quinn to...",
    #         "trailer": null,
    #         "language": "English",
    #         "mpa_rating": "PG-13",
    #         "background_image": null,
    #         "small_cover_image": null,
    #         "large_cover_image": null,
    #         "magnets": Array[2][
    #             {
    #                 "link": null,
    #                 "quality": null,
    #                 "source": null,
    #                 "seeds": null,
    #                 "peers": null,
    #                 "hash": null,
    #                 "size": null,
    #                 "size_bytes": null,
    #                 "date_created": null,
    #                 "timestamp_created": null,
    #                 "_link": "magnet:?xt=urn:btih:9687572B9D76F639BA9703CA229EC4A81DBF836A&dn=Batman+and+Harley+Quinn+2017",
    #                 "_quality": "720p",
    #                 "_source": "yts",
    #                 "_seeds": 1212,
    #                 "_peers": 230,
    #                 "_size": "548.96 MB",
    #                 "_size_bytes": 575626281,
    #                 "_date_created": "",
    #                 "_timestamp_created": "",
    #                 "_hash": "9687572B9D76F639BA9703CA229EC4A81DBF836A",
    #                 "id": "None"
    #             },
    #             ...
    #         ],
    #         "actors": Array[4][
    #             "Kevin Conroy",
    #             "Melissa Rauch",
    #             "Paget Brewster",
    #             "Loren Lester"
    #         ],
    #         "id": "59b80872c80975a42e456a28"
    #     },
    #     ...
    #   ],
    # "id": "None"

    # https://github.com/afrase/kodiswift/blob/master/docs/item.rst#the-listitem
    # http://mirrors.kodi.tv/docs/python-docs/16.x-jarvis/xbmcgui.html#ListItem-setInfo
    title = data.get('title') or 'Title unknown'
    description = data.get('desc') or data.get('description') or data.get('synopsis')
    if not description or description == 'None':
        description = 'Description is not available'

    info = {
        'title': title,
        'plot': description,
        'language': (data.get('language') or 'en').lower()
    }

    description = "\n" + description + "\n"

    background_image = None
    large_cover_image = None
    small_cover_image = None

    if data.get('tags'):
        tags = data['tags']
        description = "Tags: %s\n%s" % (", ".join(tags), description)

    label = title
    if data.get('items'):
        length = len(data['items'])
        label = '[B]%s[/B]  [COLOR %s](%s %s)[/COLOR]' % (label, ADDITIONS_COLOR, length, 'item' if length == 1 else 'items')

        for pitem in data['items']:
            if not pitem:
                continue

            if pitem.get('title'):
                description = description + "\n - " + pitem['title'].strip()

            if not background_image and pitem.get('background_image'):
                background_image = pitem['background_image']

            if not large_cover_image and pitem.get('large_cover_image'):
                large_cover_image = pitem['large_cover_image']

            if not small_cover_image and pitem.get('small_cover_image'):
                small_cover_image = pitem['small_cover_image']

    description = description.strip()
    info['plot'] = description

    playlist_id = "%s: %s" % (_get_entry_id_raw(data), data.get('title'))

    result = {
        'label': label,
        'label2': description,
        'info': info,
        'path': url_for('action_category_playlist_show', playlist_id=playlist_id, category=category),
        '__playlist_id__': playlist_id,
    }

    if background_image:
        result['fanart'] = background_image

    if large_cover_image:
        result['poster'] = large_cover_image
        result['thumbnail'] = large_cover_image
        result['icon'] = large_cover_image

    if small_cover_image:
        result['favicon'] = small_cover_image
        if not large_cover_image:
            result['poster'] = small_cover_image
            result['thumbnail'] = small_cover_image
            result['icon'] = small_cover_image

    # log(result)
    return prepare_list_item(result, category, is_structural=True)


def create_kodi_magnet_list(magnet_links, entry_id, season=NONE, episode=NONE):
    if not magnet_links or not entry_id:
        return result_nothing_found("torrents")

    assert isinstance(magnet_links, list)

    is_tvshow = episode and episode != NONE
    category = 'tvshows' if is_tvshow else 'movies'

    api_data = _get_stored_data_for_id(entry_id, category)
    if is_tvshow:
        result_base = make_tvshow_item(api_data, as_stub=True)
    else:
        result_base = make_movie_item(api_data, as_stub=True)

    get_tvshow_magnets_for_id(entry_id, season, episode)

    items = []
    i = 0
    for magnet_item in magnet_links:
        assert isinstance(magnet_item, list)

        item = copy.copy(result_base)

        link = magnet_item[0]
        title = magnet_item[1]

        if is_tvshow:
            item['path'] = url_for('action_tvshow_episode_exact', entry_id=entry_id, season=season, episode=episode, magnet_link=link)
        else:
            item['path'] = url_for('action_movie_exact', entry_id=entry_id, magnet_link=link)

        item['label'] = '[B]%s[/B]' % title if i == 0 else title
        item['label2'] = title
        item['__magnet_link__'] = link
        items.insert(len(items), prepare_list_item(item, category, is_structural=False))
        i = i+1

    return items or result_nothing_found("torrents")


# == Utils ==

def _get_playlist_data(playlist_id):
    data = store.get('store')
    if data:
        log("Looking for playlist %s in list with size %s" % (playlist_id, len(data)))
        for item in data:
            _pl_id = "%s: %s" % (_get_entry_id_raw(item), item.get('title'))
            if _pl_id == playlist_id:
                return item
    else:
        log("Looking for playlist %s in the empty data list!" % playlist_id, 3)
    return None


def _get_stored_data_for_id(_id, category='movies'):
    data = store.get('store')
    if data:
        log("Looking for %s in list with size %s" % (_id, len(data)))
        for item in data:
            # Playlist item
            if item.get('items'):
                for pitem in item['items']:
                    if _has_entry_id(pitem, _id):
                        return pitem

            # Raw item
            if _has_entry_id(item, _id):
                return item
    else:
        log("Looking for %s in the empty data list!" % _id, 3)

    # Viewed item
    viewed_storage = store.get('viewed')
    if viewed_storage:
        log("Looking for %s in viewed storage" % _id)
        for category in viewed_storage:
            viewed = viewed_storage.get(category)
            if not viewed:
                continue

            for v_item in viewed:
                if not v_item:
                    continue

                v_id, v_data = v_item
                if not v_data:
                    continue

                if v_id == _id or _has_entry_id(v_data, _id):
                    return v_data

    return load_item_by_id(_id, category)


def _get_magnet_from_magnets(data, exact=None):
    magnets_list = []

    if data and data.get('magnets'):
        for magnet in data['magnets']:
            magnet_hash = magnet.get('hash') or magnet.get('_hash')
            magnet_link = magnet.get('link') or magnet.get('_link')

            torrent_link = 'http://itorrents.org/torrent/%s.torrent' % magnet_hash if magnet_hash else None

            is_found = exact and ((torrent_link and torrent_link == exact) or magnet_link == exact)

            if magnet_hash:
                magnets_list.insert(len(magnets_list), _get_magnet_list_item(torrent_link, magnet))
                if not is_found:
                    continue

                if TORRENT_FILES_LOOKUP and not LOCAL_TEST_MODE:
                    opener = urllib2.build_opener(urllib2.HTTPHandler)
                    request = urllib2.Request(torrent_link)
                    request.add_header('User-Agent', USER_AGENT)
                    request.get_method = lambda: 'HEAD'
                    # noinspection PyBroadException,PyStatementEffect
                    try:
                        opener.open(request, timeout=REQUESTS_TIMEOUT).read()
                        log("Opening torrent file link: %s" % torrent_link)
                        return torrent_link
                    except Exception:
                        pass

            if magnet_link:
                magnets_list.insert(len(magnets_list), _get_magnet_list_item(magnet_link, magnet))
                if not is_found:
                    continue

                log("Opening magnet link: %s" % magnet_link)
                return magnet_link

    # log("magnets_list: %s" % magnets_list)
    if magnets_list:
        assert isinstance(magnets_list, list)

        if len(magnets_list) == 1:
            return magnets_list[0][0]

        magnets_list = sorted(magnets_list, key=lambda mg: -mg[2])
        return magnets_list

    return None


def _get_magnet_list_item(magnet_link, magnet_data):
    _seeds = magnet_data.get('seeds') or magnet_data.get('_seeds')
    seeds = 0
    if _seeds:
        try:
            seeds = int(_seeds)
        except:
            pass

    _peers = magnet_data.get('peers') or magnet_data.get('_peers')
    peers = 0
    if _peers:
        try:
            peers = int(_peers)
        except:
            pass

    size = magnet_data.get('size') or magnet_data.get('_size')
    if not size or size == '?':
        size = 'unknown size'

    quality = magnet_data.get('quality') or magnet_data.get('_quality')
    if not quality or quality == '?':
        quality = 'unknown quality'

    title = '%s, %s' % (quality, size)
    if seeds > 0:
        if peers > 0:
            title = '%s peers, %s' % (peers, title)
        title = '%s seeders, %s' % (seeds, title)

    return [magnet_link, title, seeds, peers]


def get_movie_magnets_for_id(_id, magnet_link=None, track=False):
    movie = _get_stored_data_for_id(_id, category='movies')
    magnet_links = _get_magnet_from_magnets(movie, magnet_link)

    # track only when we have a single magnet_link to open,
    # so it really will be opened by user
    if track and not isinstance(magnet_links, list) and movie:
        track_view(_id, movie, category='movies')

    return magnet_links


def get_tvshow_magnets_for_id(_id, season=None, episode=None, magnet_link=None, track=False):
    show = _get_stored_data_for_id(_id, category='tvshows')
    if show and show.get('seasons'):
        for season_key in show['seasons']:
            if not season or season == NONE or season_key == season:
                eposodes = show['seasons'][season_key]
                for eposode_key in eposodes:
                    if not episode or episode == NONE or eposode_key == episode:
                        episode_data = eposodes[eposode_key]
                        magnet_links = _get_magnet_from_magnets(episode_data, magnet_link)
                        if magnet_links:
                            # track only when we have a single magnet_link to open,
                            # so it really will be opened by user
                            if track and not isinstance(magnet_links, list) and show:
                                track_view(_id, show, category='tvshows')

                            return magnet_links

                        if episode:
                            break
                if season:
                    break
    return None


def result_error(error, category, do_notice=True):
    if do_notice:
        notice(error)
    return [prepare_list_item({
        'label': error,
        'path': NOTHING_FOUND_PATH,
    }, category, is_structural=True)]


def result_not_supported_category(category):
    return result_error('Not supported category: %s' % category, 'movies')


def result_nothing_found(category='movies'):
    if category != 'tvshows' and category != 'movies':
        name = category
        category = 'movies'
    else:
        name = 'TV Shows' if category == 'tvshows' else 'Movies'

    label = 'No %s found :(' % name
    return result_error(label, category, do_notice=False)


def prepare_media_info(data, category, as_stub=False):
    title = data.get('title') or data.get('_title') or 'Title unknown'

    synopsis = data.get('synopsis') or data.get('_synopsis')
    if synopsis == 'None' or synopsis == 'N/A':
        synopsis = None

    description = data.get('description') or data.get('_description') or data.get('desc') or data.get('_desc')
    if description == 'None' or description == 'N/A':
        description = None

    description = description or synopsis or 'Description is not available'
    synopsis = synopsis or description or 'Synopsis is not available'

    info = {
        'title': title,
        'tvshowtitle': title,
        'plot': description,
        'plotoutline': synopsis,
        'tagline': synopsis,
        'language': (data.get('language') or 'en').lower()[0:2],
    }

    description = "\n" + description

    if data.get('imdb_code'):
        info['code'] = data['imdb_code']

    if data.get('mpa_rating'):
        info['mpaa'] = data['mpa_rating']

    if data.get('ratings'):
        ratings = data['ratings']
        imdb_rating = None
        if isinstance(ratings, dict):
            imdb_rating = ratings.get('imdb')
        elif isinstance(ratings, list):
            for ritem in ratings:
                if isinstance(ritem, dict) and ritem.get('imdb'):
                    imdb_rating = ritem['imdb']
        if imdb_rating and imdb_rating != 'N/A':
            description = "IMDB: %s\n%s" % (imdb_rating, description)
            info['rating'] = float(imdb_rating)

    if data.get('genres'):
        genres = data['genres']
        if 'N/A' in genres:
            genres.remove('N/A')
        if genres:
            genres = ", ".join(genres)
            description = "Genres: %s\n%s" % (genres, description)
            info['genre'] = genres

    if data.get('year') and not as_stub:
        try:
            info['year'] = int(data['year'])
        except:
            # u'2017–'
            parts = data['year'].split(u'–', 2)
            if len(parts) >= 2:
                info['year'] = int(parts[1] if parts[1] else parts[0])

    if data.get('trailer'):
        info['trailer'] = 'plugin://plugin.video.youtube/?action=play_video&videoid=' + data['trailer']

    if data.get('actors'):
        info['cast'] = data['actors']

    if data.get('timeadded'):
        # string (Y-m-d h:m:s = 2009-04-05 23:16:04)
        info['dateadded'] = datetime.date.fromtimestamp(data['timeadded']).strftime('%Y-%m-%d %H:%M:%S')

    if data.get('magnets'):
        sizes = [int(magnet.get('_size_bytes') or magnet.get('size_bytes') or 0) for magnet in data['magnets']]
        sizes = [bytes_num for bytes_num in sizes if bytes_num > 0]
        if sizes:
            info['size'] = sorted(sizes)[0]

    if as_stub:
        description = "%s\n%s" % (title, description)

    label = title
    if data.get('seasons'):
        length = len(data['seasons'])
        if length or category == 'tvshows':
            label = '[B]%s[/B]  [COLOR %s](%s %s)[/COLOR]' % (label, ADDITIONS_COLOR, length, 'season' if length == 1 else 'seasons')

    description = description.strip()
    info['plot'] = description

    entry_id = _get_entry_id(data)
    result = {
        'label': label,
        'label2': description,
        'info': info,
        '__entry_id__': entry_id
    }

    result = prepare_list_item(result, category, api_data=data, is_structural=False)
    return result


def prepare_list_item(item, category, mediatype=None, is_structural=True, api_data=None):
    if item:
        if api_data:
            if api_data.get('background_image'):
                item['fanart'] = api_data['background_image']

            if api_data.get('large_cover_image'):
                large_cover_image = api_data['large_cover_image']
                item['poster'] = large_cover_image
                item['thumbnail'] = large_cover_image
                item['icon'] = large_cover_image

            if api_data.get('small_cover_image'):
                small_cover_image = api_data['small_cover_image']
                item['favicon'] = small_cover_image
                if not item.get('poster'):
                    item['poster'] = small_cover_image
                    item['thumbnail'] = small_cover_image
                    item['icon'] = small_cover_image

        if not item.get('fanart'):
            if is_structural:
                item['fanart'] = SITO_FANART_IMAGE
            else:
                item['fanart'] = item.get('poster') or SITO_FANART_IMAGE

        if not item.get('icon'):
            item['icon'] = image_resource_url(SITO_CATEGORY_ICON % category)

        if not item.get('poster'):
            item['poster'] = item['icon']

        # thumb, poster, banner, fanart, clearart, clearlogo, landscape, icon
        thumbnail = item.get('thumbnail') or item.get('thumb')
        if thumbnail:
            item['thumbnail'] = thumbnail
            item['thumb'] = thumbnail

        # if not is_structural:
        item['info_type'] = 'video'

        item['is_playable'] = False

        # imdb_code = (api_data and api_data.get('imdb_code')) or None
        if not is_structural:
            # entry_id = _get_entry_id(item)
            # item['context_menu'] = [
            #     ('Add to favorites', 'RunScript(%s, custom_action, add_to_favorites, %s)' % (PLUGIN_ID, entry_id))
            # ]
            # item['replace_context_menu'] = True
            pass

        # Kodi item info docs
        # http://mirrors.kodi.tv/docs/python-docs/16.x-jarvis/xbmcgui.html#ListItem-setInfo
        if not item.get('info'):
            item['info'] = {}

        info = item['info']
        if not info.get('mediatype'):
            # "video", "movie", "tvshow", "season", "episode" or "musicvideo"
            if category != 'tvshows':
                mediatype = 'movie'
            elif not mediatype:
                mediatype = 'tvshow'

            info['mediatype'] = mediatype

        if not info.get('language'):
            info['language'] = 'en'

    return item


def _has_entry_id(data, entry_id):
    return _get_entry_id(data) == entry_id or _get_entry_id_raw(data) == entry_id

def _get_entry_id(data):
    # Uses IMDB code everywhere instead of simple server ID
    return data.get('imdb_code') or _get_entry_id_raw(data)

def _get_entry_id_raw(data):
    return data.get('__entry_id__') or data.get('_id') or data['id']
