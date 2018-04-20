# -*- coding: utf-8 -*-
import os
import sys
import time

import sito
from kodiswift import Plugin, xbmcgui, xbmc

DEBUG = False

plugin = Plugin()
last_category = None


def log(txt, level=xbmc.LOGWARNING):
    message = '%s: %s' % (plugin.name, str(txt).encode('ascii', 'ignore'))
    # addons should use the xbmc.log() method to write to the logfile and use the debug logging level only.
    # print statements should not be used.
    xbmc.log(msg=message, level=level if DEBUG else xbmc.LOGDEBUG)
    if level >= xbmc.LOGERROR:
        notice_text = "Error detected, please try again later"
        # notice_text = "%s.\nDetails: %s" % (notice_text, txt)
        notice(notice_text, "Addon Error")


def notice(message, heading="", delay=4000):
    plugin.notify(message, heading, delay, '')


def get_os_name():
    try:
        if xbmc.getCondVisibility("system.platform.android") or sito.is_android():
            return "android"
        elif xbmc.getCondVisibility("system.platform.linux"):
            return "linux"
        elif xbmc.getCondVisibility("system.platform.xbox"):
            return "xbox"
        elif xbmc.getCondVisibility("system.platform.windows"):
            return "windows"
        elif xbmc.getCondVisibility("system.platform.osx"):
            return "darwin"
        elif xbmc.getCondVisibility("system.platform.ios"):
            return "ios"
        elif xbmc.getCondVisibility("system.platform.atv2"):
            # Apple TV 2
            return "atv2"
    except Exception as ex:
        log("get_os_name error: %s" % ex, level=xbmc.LOGERROR)
    return "unknown"


os_name = get_os_name()
os_is_android = os_name == 'android' or sito.is_android()

NATIVE_PATH = xbmc.translatePath(plugin.addon.getAddonInfo('path'))

bitx_package = 'tv.bitx.media'
bitx_play_link = 'https://play.google.com/store/apps/details?id=tv.bitx.media&referrer=utm_source%3Dkodi.sito.tv'

bitx_is_installed = False
try:
    bitx_package_path = os.popen('pm path %s' % bitx_package).read()
    if bitx_package_path:
        bitx_is_installed = True

    log("BitX application path: %s" % bitx_package_path, level=xbmc.LOGINFO)
except Exception as e:
    log("Android pm path error: %s" % e, level=xbmc.LOGERROR)


def image_resource_url(image_resource):
    return os.path.join(NATIVE_PATH, image_resource)


class ViewMode(object):
    ListView = None
    IconWall = 50


def kodi_go_back():
    # Go back in navigation.
    xbmc.executebuiltin("Action(Back)")


def start_bitx(magnet_link):
    if os_is_android and bitx_is_installed:
        # noinspection PyBroadException
        try:
            notice('Starting BitX', 'Info')

            # StartAndroidActivity(package,[intent,dataType,dataURI])
            # Launch an Android native app with the given package name.
            # Optional parms (in order): intent, dataType, dataURI.
            # example: StartAndroidActivity(com.android.chrome,android.intent.action.VIEW,,http://kodi.tv/)	v13 Addition
            intent = "android.intent.action.VIEW"
            xbmc.executebuiltin('XBMC.StartAndroidActivity("%s", "%s", , "%s")' % (bitx_package, intent, magnet_link))
            return
        except Exception as ex:
            log("Android intent error: %s" % ex, level=xbmc.LOGERROR)

    if os_is_android:
        xbmcgui.Dialog().ok('BitX App Not Installed', 'You need to install the "BitX" application to watch this content.')
    else:
        xbmcgui.Dialog().ok(
            'Android and BitX app are requred',
            'You should run this plugin on the android device with the "BitX" application installed to watch this content.')

    # xbmc.executebuiltin('XBMC.StartAndroidActivity("com.android.vending","android.intent.action.VIEW",,"market://details?id=%s")' % package)
    open_web_url(bitx_play_link)


def open_web_url(url):
    if os_name == 'windows' or os_name == 'linux' or os_name == 'darwin' or os_name == 'ios' or os_name == 'atv2':
        try:
            import webbrowser
            webbrowser.open_new(url)
            return
        except Exception as ex:
            log("Android intent error: %s" % ex, level=xbmc.LOGERROR)

    xbmc.executebuiltin('XBMC.StartAndroidActivity(,"android.intent.action.VIEW", ,"%s")' % url)


CUSTOM_API_URL = plugin.get_setting('api_url', unicode)
CACHE_ID_SUFFIX = ''
if CUSTOM_API_URL:
    sito.DEFAULT_API_URL = CUSTOM_API_URL
    try:
        import hashlib
        CACHE_ID_SUFFIX = '-' + hashlib.md5(CUSTOM_API_URL.encode('utf-8')).hexdigest()
    except Exception as ex:
        log("BitX hashlib error: %s" % ex, level=xbmc.LOGERROR)
        CACHE_ID_SUFFIX = '-' + CUSTOM_API_URL.replace(':', '_').replace('/', '-').replace('\\', '-')


sito.log = log
sito.notice = notice
sito.image_resource_url = image_resource_url
sito.url_for = plugin.url_for
sito.store = plugin.get_storage('basic_cache' + CACHE_ID_SUFFIX)
sito.requests_cache = plugin.get_storage('requests_cache', ttl=60*4)

sito.SITO_FANART_IMAGE = plugin.addon.getAddonInfo('fanart') or image_resource_url(sito.SITO_FANART_IMAGE)

NONE = sito.NONE

MOVIES_COLOR = 'FFFFFFFF'  # White
TVSHOWS_COLOR = 'FFFFFFFF'  # White
GENRE_COLOR = 'FFFFFFFF'  # White
ALPHABET_COLOR = 'FFFFFFFF'  # White
COLLECTIONS_COLOR = 'FFFFFFFF'  # White
SEARCH_COLOR = 'FFB8E986'  # Yellow
LAST_VIEWED_COLOR = 'FFB8E986'  # Yellow
NEW_LABEL_COLOR = 'FFFF0000'  # Simple red


# /..

@plugin.route('/', root=True)
def action_index():
    result = [
        sito.prepare_list_item({
            'label': '[COLOR %s]Movies[/COLOR]' % MOVIES_COLOR,
            'label2': 'Label2',
            'path': plugin.url_for('action_category', category='movies'),
            'poster': plugin.addon.getAddonInfo('icon'),
            'info': {'plot': 'Find favorite movies'}
        }, 'movies'),

        sito.prepare_list_item({
            'label': '[COLOR %s]TV Shows[/COLOR]' % TVSHOWS_COLOR,
            'label2': 'Label2',
            'path': plugin.url_for('action_category', category='tvshows'),
            'poster': plugin.addon.getAddonInfo('icon'),
            'info': {'plot': 'Find favorite TV Shows'}
        }, 'tvshows')
    ]
    log("index route")
    return plugin.finish(result, view_mode=ViewMode.IconWall)


# /<category>

@plugin.route('/<category>')
def action_category(category):
    if category != 'movies' and category != 'tvshows':
        return sito.result_not_supported_category(category)

    name = 'TV Shows' if category == 'tvshows' else 'Movies'
    all_color = TVSHOWS_COLOR if category == 'tvshows' else MOVIES_COLOR

    result = [
        sito.prepare_list_item({
            'label': '[COLOR %s]All %s[/COLOR]' % (all_color, name),
            'path': plugin.url_for('action_category_media', category=category),
            'info': {'plot': 'All %s' % name}
        }, category),

        sito.prepare_list_item({
            'label': '[COLOR %s]Choose genre[/COLOR]' % GENRE_COLOR,
            'path': plugin.url_for('action_category_genres', category=category),
            'info': {'plot': 'Find %s by genre' % name}
        }, category),

        sito.prepare_list_item({
            'label': '[COLOR %s]Choose by alphabet[/COLOR]' % ALPHABET_COLOR,
            'path': plugin.url_for('action_category_alphabet', category=category),
            'info': {'plot': 'Find %s by alphabet' % name}
        }, category),

        sito.prepare_list_item({
            'label': '[COLOR %s]%s Collections[/COLOR] [COLOR %s]!! NEW !![/COLOR]' % (COLLECTIONS_COLOR, name, NEW_LABEL_COLOR),
            'path': plugin.url_for('action_category_playlists', category=category),
            'info': {'plot': '%s Collections' % name}
        }, category),

        sito.prepare_list_item({
            'label': '[COLOR %s]Search[/COLOR]' % SEARCH_COLOR,
            'path': plugin.url_for('action_category_search', category=category),
            'info': {'plot': 'Find favorite %s' % name}
        }, category),

        sito.prepare_list_item({
            'label': '[COLOR %s]Last viewed %s[/COLOR] [COLOR %s]!! NEW !![/COLOR]' % (LAST_VIEWED_COLOR, name, NEW_LABEL_COLOR),
            'path': plugin.url_for('action_category_last_viewed', category=category),
            'info': {'plot': 'Last viewed %s' % name}
        }, category),

        sito.prepare_list_item({
            'label': '[COLOR %s]Plugin settings[/COLOR]' % all_color,
            'path': plugin.url_for('action_custom_action', action='Addon.OpenSettings(%s)' % sito.PLUGIN_ID),
            'info': {'plot': 'Plugin settings'}
        }, category)
    ]

    log("index %s route" % name)
    return plugin.finish(result, view_mode=ViewMode.ListView)


# /<category>/genres

@plugin.route('/<category>/genres')
def action_category_genres(category):
    if category != 'movies' and category != 'tvshows':
        return sito.result_not_supported_category(category)

    name = 'TV Shows' if category == 'tvshows' else 'Movies'
    all_color = TVSHOWS_COLOR if category == 'tvshows' else MOVIES_COLOR

    result = [
        sito.prepare_list_item({
            'label': '[COLOR %s][B]Any genre[/B][/COLOR]' % all_color,
            'path': plugin.url_for('action_category_media', category=category),
            'info': {'plot': '%s of any genre' % name}
        }, category)
    ]

    for genre in sito.genres_list:
        result.insert(len(result), sito.prepare_list_item({
            'label': "[COLOR %s]%s[/COLOR]" % (GENRE_COLOR, genre),
            'path': plugin.url_for('action_category_media_genre', category=category, genre=genre),
            'info': {'plot': '%s %s' % (genre, name)}
        }, category))

    log("genres %s route" % name)
    return result


# /<category>/alphabet

@plugin.route('/<category>/alphabet')
def action_category_alphabet(category):
    if category != 'movies' and category != 'tvshows':
        return sito.result_not_supported_category(category)

    name = 'TV Shows' if category == 'tvshows' else 'Movies'
    all_color = TVSHOWS_COLOR if category == 'tvshows' else MOVIES_COLOR

    result = [
        sito.prepare_list_item({
            'label': '[COLOR %s]All %s[/COLOR]' % (all_color, name),
            'path': plugin.url_for('action_category_media', category=category),
            'info': {'plot': 'All %s' % name}
        }, category)
    ]

    for letter in "A,B,C,D,E,F,G,H,I,J,K,L,M,N,O,P,Q,R,S,T,U,V,W,X,Y,Z".split(","):
        result.insert(len(result), sito.prepare_list_item({
            'label': "[B]%s[/B]" % letter,
            'path': sito.url_for('action_category_media_search', category=category, search_term=letter),
            'info': {'plot': '%s by the [B]%s[/B] letter' % (name, letter)}
        }, category))

    log("alphabet %s route" % name)
    return result


# /<category>/last_viewed

@plugin.route('/<category>/last_viewed')
def action_category_last_viewed(category):
    log('show last viewed %s' % category)
    if category != 'movies' and category != 'tvshows':
        return sito.result_not_supported_category(category)

    items = sito.create_kodi_last_viewed_list(category)
    return plugin.finish(items, update_listing=False)


# /<category>/playlists/list_..

@plugin.route('/<category>/playlists/list_-_1', name='action_category_playlists', options={'page': '1', 'search_term': NONE})
@plugin.route('/<category>/playlists/list_<search_term>_1', name='action_category_playlists_search', options={'page': '1'})
@plugin.route('/<category>/playlists/list_<search_term>_<page>')
def action_category_playlists_page(category, page, search_term):
    log('show %s playlists at %s page // search_term=%s' % (category, page, search_term))

    if category != 'movies' and category != 'tvshows':
        return sito.result_not_supported_category(category)

    page = int(page)  # all url params are strings by default

    # sort_params = 'year:desc,rating:desc,title:asc'
    sort_params = 'updated_date:desc,created_date:desc'
    parameters = {'page': page, 'sort': sort_params, 'limit': '25'}

    if search_term and search_term != NONE:
        # Alphabet lookup
        if len(search_term) == 1:
            search_term = "^" + search_term

        parameters['filter'] = '{"title":"%s"}' % search_term

    request_key = 'movie' if category == 'movies' else 'series'
    data = sito.api('%s/playlists' % request_key, params=parameters)
    items = sito.create_kodi_playlists_list(data, page, category, search_term)
    return plugin.finish(items, update_listing=False)


# /<category>/playlists/show_playlist_..

@plugin.route('/<category>/playlists/show_playlist_<playlist_id>')
def action_category_playlist_show(category, playlist_id):
    log('show %s playlist %s' % (category, playlist_id))

    if category != 'movies' and category != 'tvshows':
        return sito.result_not_supported_category(category)

    items = sito.create_kodi_playlist_list(playlist_id, category)
    # sort_methods=['title', 'date']
    return plugin.finish(items, update_listing=False)


# /<category>/search

@plugin.route('/<category>/search')
def action_category_search(category):
    if category != 'movies' and category != 'tvshows':
        return sito.result_not_supported_category(category)

    name = 'TV Shows' if category == 'tvshows' else 'Movies'
    while True:
        search_term = plugin.keyboard('', 'Search for %s' % name)
        if search_term is None:
            kodi_go_back()
            return

        if len(search_term.decode('utf-8')) >= 1:
            sito.store['last_search_term'] = search_term
            break
        else:
            notice('Enter more characters to search for', 'Search')

    plugin.redirect(sito.url_for('action_category_media_search', category=category, search_term=search_term))


# /<category>/list_..

@plugin.route('/<category>/list_-_-_1', name='action_category_media', options={'genre': NONE, 'page': '1', 'search_term': NONE})
@plugin.route('/<category>/list_<genre>_-_1', name='action_category_media_genre', options={'page': '1', 'search_term': NONE})
@plugin.route('/<category>/list_-_<search_term>_1', name='action_category_media_search', options={'genre': NONE, 'page': '1'})
@plugin.route('/<category>/list_<genre>_<search_term>_<page>')
def action_category_media_page(category, genre, page, search_term):
    log('show category %s at %s page // genre=%s / search_term=%s' % (category, page, genre, search_term))

    if category != 'movies' and category != 'tvshows':
        return sito.result_not_supported_category(category)

    page = int(page)  # all url params are strings by default

    # sort_params = 'year:desc,rating:desc,title:asc'
    sort_params = 'year:desc,rating:desc'
    parameters = {'page': page, 'sort': sort_params, 'limit': '40'}

    # Alphabet lookup
    if search_term and search_term != NONE and len(search_term) == 1:
        search_term = "^" + search_term

    if genre and genre != NONE and search_term and search_term != NONE:
        parameters['filter'] = '{"genres":"%s","title":"%s"}' % (genre, search_term)
    if genre and genre != NONE:
        parameters['filter'] = '{"genres":"%s"}' % genre
    elif search_term and search_term != NONE:
        parameters['filter'] = '{"title":"%s"}' % search_term

    data = sito.api(category, params=parameters)
    items = sito.create_kodi_list(data, page, category, genre, search_term)

    # sort_methods=['title', 'date']
    return plugin.finish(items, update_listing=False)


# /tvshows/show/..

@plugin.route('/tvshows/show_<entry_id>', name='action_tvshow', options={'season': '', 'episode': '', 'magnet_link': None})
@plugin.route('/tvshows/show_<entry_id>/<season>', name='action_tvshow_season', options={'episode': '', 'magnet_link': None})
@plugin.route('/tvshows/show_<entry_id>/<season>/<episode>', name='action_tvshow_episode', options={'magnet_link': None})
@plugin.route('/tvshows/show_<entry_id>/<season>/<episode>/<magnet_link>')
def action_tvshow_episode_exact(entry_id, season, episode, magnet_link):
    log("show tvshow %s, season = %s, episode=%s" % (entry_id, season, episode))

    if episode and episode != sito.NONE:
        magnet_links = sito.get_tvshow_magnets_for_id(entry_id, season, episode, magnet_link, track=True)
        if not isinstance(magnet_links, list):
            return open_magnet(magnet_links)

        items = sito.create_kodi_magnet_list(magnet_links, entry_id, season, episode)
        return plugin.finish(items, update_listing=False)

    if not season or season == sito.NONE:
        items = sito.create_kodi_tvshow_seasons_list(entry_id)
    else:
        items = sito.create_kodi_tvshow_episodes_list(entry_id, season)

    # sort_methods=['title', 'date']
    return plugin.finish(items, update_listing=False)


# /movies/show/..

@plugin.route('/movies/show_<entry_id>', name='action_movie', options={'magnet_link': None})
@plugin.route('/movies/show_<entry_id>/<magnet_link>')
def action_movie_exact(entry_id, magnet_link):
    magnet_links = sito.get_movie_magnets_for_id(entry_id, magnet_link, track=True)
    if not isinstance(magnet_links, list):
        return open_magnet(magnet_links)

    items = sito.create_kodi_magnet_list(magnet_links, entry_id, season=NONE, episode=NONE)
    return plugin.finish(items, update_listing=False)


# /custom_action/..

@plugin.route('/custom_action/<action>')
def action_custom_action(action):
    log("action_custom_action: %s" % action)
    xbmc.executebuiltin(action)


# Utils

def custom_action(argv=None):
    log("custom_action: %s" % argv)
    # ['addon.py', 'custom_action', 'add_to_favorites', '5a09f7a3c80975a42e45870e']
    if argv and len(argv) > 2:
        action = argv[2]
        if action == 'add_to_favorites':
            if len(argv) > 3 and argv[3]:
                entry_id = argv[3]
                log("add_to_favorites by EntryID: %s" % entry_id)

        elif action == 'update_plugin':
            check_update(force=True)

        elif action == 'authorization':
            text = "Authorization is not supported yet :("
            notice(text, "Not supported")
            log(text, level=xbmc.LOGWARNING)

        elif action == 'show_log':
            text = "Log opening is not supported yet :("
            notice(text, "Not supported")
            log(text, level=xbmc.LOGWARNING)

        elif action == 'bug_report':
            report_text = plugin.keyboard('', 'Bug report')
            if report_text and len(report_text.decode('utf-8')) >= 1:
                # {"title":"SiTo Feedback","description":"","email":"unknown"}
                sito.api('feedback', '{"title":"SiTo Feedback","description":"'+report_text.replace('"', '\\"')+'","email":"unknown"}', method='POST')

    pass


def open_magnet(magnet_link):
    log("open magnet: %s" % magnet_link)
    if magnet_link:
        try:
            start_bitx(magnet_link)
            kodi_go_back()
            return
        except Exception as ex:
            log("BitX magnet start error: %s" % ex, level=xbmc.LOGERROR)

    notice("Can't play this item, sorry :(", "Problem", 2500)
    kodi_go_back()


def check_update(force=False):
    action_text = "Updating plugins"
    if force:
        notice(action_text)
        return

    current_time = int(time.time())

    # Test the "check" status itself
    last_update_check = plugin.get_setting('last_update_check_time', str)
    last_update_check = int(last_update_check) if last_update_check else 0
    if current_time - last_update_check < 3600:
        # checked already
        return
    # Save time of this check
    plugin.set_setting('last_update_check_time', str(current_time))

    # Now check if we need to update plugin
    last_update_time = plugin.get_setting('last_update_time', str)
    last_update_time = int(last_update_time) if last_update_time else 0
    start_update = False
    # Auto-update once in 24 hours
    if current_time - last_update_time >= 86400:
        start_update = True

    else:
        vinfo = sito.get_server_versions()
        if vinfo and vinfo.get('min_version'):
            min_version = vinfo['min_version']
            current_version = plugin.version
            try:
                from distutils.version import StrictVersion
                if StrictVersion(min_version) > StrictVersion(current_version):
                    log("Current version should be updated to %s" % min_version)
                    start_update = True
            except Exception as ex:
                log("StrictVersion error: %s" % ex, level=xbmc.LOGERROR)

    if start_update:
        plugin.set_setting('last_update_time', str(current_time))
        log(action_text)
        xbmc.executebuiltin('UpdateAddonRepos')


# FIXME: Show version number in settings

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'custom_action':
        custom_action(sys.argv)
    else:
        check_update(force=False)
        plugin.run()
