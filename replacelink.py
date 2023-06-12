# Replace Tool 2023/05 Hiroyuki Ogasawara
# vim:ts=4 sw=4 et:

import sys
import os
import re
import json
from html.parser import HTMLParser
import urllib.parse
import datetime

#------------------------------------------------------------------------------
# https://192.168.2.5/blog/wp-content/uploads/2023/05/armlinux01.jpg
# http://wlog.flatlib.jp/archive/1/2006-10-23

# Media Path to WP
# Self Link to WP
# slug = 2023/05/nID

class TagParser( HTMLParser ):
    
    URLTAGS= { 'href':0, 'src':0 }
    WP_MEDIA_PATH= 'wp-content/uploads'

    def __init__( self, date, debug_flag, indexmap, datemap, account, config ):
        super().__init__()
        self.account= account
        self.SERVER= account['url']
        self.config= config
        self.BASE_HOST= self.config['base_host']
        self.MEDIA_PATH= self.config['media_path']
        self.ARCHIVE_PATH= self.config['archive_path']
        # 0000-00
        date= datetime.datetime.today().strftime( '%Y-%m' )
        self.date_path= '%s/%s' % (date[0:4],date[5:7])
        self.debug_flag= debug_flag
        self.indexmap= indexmap
        self.datemap= datemap
        if self.debug_flag:
            print( '**********', self.date_path )
        self.text= ''
        self.media_map= {}
        self.pat_self_link_date= re.compile( self.ARCHIVE_PATH + r'/(\d+)-(\d+)-(\d+)' )    # archive/1/0000-00-00
        self.pat_self_link_month= re.compile( self.ARCHIVE_PATH + r'/(\d+)-(\d+)' )         # archive/1/0000-00
        self.pat_media_file= re.compile( self.MEDIA_PATH + r'/(.+)' )                       # media/1/....
        self.pat_item_link= re.compile( r'item/(\d+)' )
        self.enter_code= False

    def encode_attr( self, attrs ):
        attr_text= ''
        for attr in attrs:
            attr_text+= ' %s="%s"' % attr
        return  attr_text

    def replace_url( self, url ):
        parse= urllib.parse.urlparse( url )
        if parse.netloc == self.BASE_HOST:
            print( 'FOUND self host [%s]' % parse.path )
            print( parse )
            # self link 0000-00-00
            pat= self.pat_self_link_date.search( parse.path )
            if pat:
                y= pat.group( 1 )
                m= pat.group( 2 )
                d= pat.group( 3 )
                return  '%s/%s/%s/%s' % (self.SERVER,y,m,d)
            # self link 0000-00
            pat= self.pat_self_link_month.search( parse.path )
            if pat:
                y= pat.group( 1 )
                m= pat.group( 2 )
                return  '%s/%s/%s' % (self.SERVER,y,m)
            # self link item
            pat= self.pat_item_link.search( parse.path )
            if pat:
                item_id= pat.group( 1 )
                if item_id in self.indexmap:
                    link_date= self.indexmap[item_id]
                    # 0000-00-00
                    y= link_date[0:4]
                    m= link_date[5:7]
                    d= link_date[8:10]
                    return  '%s/%s/%s/%s' % (self.SERVER,y,m,d)
            # media
            pat= self.pat_media_file.search( parse.path )
            if pat:
                file_name= pat.group( 1 )
                self.media_map[ file_name ]= 1
                return  '%s/%s/%s/%s' % (self.SERVER,self.WP_MEDIA_PATH,self.date_path,file_name)
            # return home
            if parse.path == '/':
                print( '*********', str(parse) )
                return  '%s' % (self.SERVER)
            # virtualpath
            if parse.path == '/index.php':
                if parse.query != '':
                    pat= self.pat_self_link_date.search( parse.query )
                    if pat:
                        y= pat.group( 1 )
                        m= pat.group( 2 )
                        d= pat.group( 3 )
                        return  '%s/%s/%s/%s' % (self.SERVER,y,m,d)
            print( '********** WARNING!!!!: unknown url', parse.path )
        return  url

    def process_attrs( self, attrs ):
        nattrs= []
        for key,val in attrs:
            if key in self.URLTAGS:
                nval= self.replace_url( val )
                if val != nval:
                    print( '   "%s" -> "%s"' % (val,nval) )
                nattrs.append( (key,nval) )
            else:
                nattrs.append( (key,val) )
        return  nattrs

    def handle_startendtag( self, tag, attrs ):
        if self.debug_flag:
            print( 'Tag   [%s](%s)' % (tag, attrs) )
        nattrs= self.process_attrs( attrs )
        if self.enter_code and tag == 'br':
            return
        self.text+= '<%s%s />' % (tag, self.encode_attr(nattrs) )

    def handle_starttag( self, tag, attrs ):
        if self.debug_flag:
            print( 'Begin [%s](%s)' % (tag,attrs) )
        nattrs= self.process_attrs( attrs )
        if tag == 'code':
            self.text+='<pre>'
            self.enter_code= True
        self.text+= '<%s%s>' % (tag, self.encode_attr(nattrs) )

    def handle_endtag( self, tag ):
        if self.debug_flag:
            print( 'End   [%s]' % tag )
        self.text+= '</%s>' % tag
        if tag == 'code':
            self.text+='</pre>'
            self.enter_code= False

    def handle_data( self, data ):
        #print( 'Data ', data )
        self.text+= data

    def handle_comment( self, data ):
        if self.debug_flag:
            print( 'Comment "%s"' % data )
        self.text+= '<!-- %s -->' % data

    def get_text( self ):
        return  self.text

    def get_media( self ):
        return  list(self.media_map.keys())


#------------------------------------------------------------------------------

class ReplaceLink:

    def __init__( self, options ):
        self.options= options
        self.load_settings()
        self.load_datemap()
        self.debug_flag= options['debug']
        if not os.path.exists( 'item2' ):
            os.mkdir( 'item2' )
        self.set_account( options['host'] )
        self.init_replace_tags()
        self.base_host= self.config['base_host']
        media_path= self.config['media_path']
        self.media_url= self.base_host
        if media_path != '':
            self.media_url= self.base_host + '/' + media_path

    #--------------------------------------------------------------------------

    def load_settings( self ):
        self.settings= None
        self.config= { 'blog_id': 1, 'base_host': None, 'media_path': '', 'archive_path': '' }
        settings_file= 'settings.json'
        with open( settings_file, 'r', encoding='utf-8') as fi:
            self.settings= json.loads( fi.read() )
            self.config= self.settings['config']
            return  True
        print( 'open error: %s' % settings_file )
        return  False

    def set_account( self, name ):
        self.account= None
        if name in self.settings:
            self.account= self.settings[name]
            return  True
        print( 'account error: %s' % name )
        return  False

    #--------------------------------------------------------------------------

    def save_json( self, item ):
        save_name= 'item2/%s.json' % item['inumber']
        with open( save_name, 'w', encoding='utf-8' ) as fo:
            fo.write( json.dumps( item, sort_keys=True, indent=4 ) )

    def load_json( self, index ):
        load_name= 'item/%d.json' % index
        with open( load_name, 'r', encoding='utf-8' ) as fi:
            obj= json.loads( fi.read() )
            return  obj
        return  None

    def load_datemap( self ):
        self.datemap= None
        self.indexmap= None
        file_name= 'item/date.json'
        with open( file_name, 'r', encoding='utf-8' ) as fi:
            self.datemap= json.loads( fi.read() )
        file_name= 'item/index.json'
        with open( file_name, 'r', encoding='utf-8' ) as fi:
            self.indexmap= json.loads( fi.read() )

    #--------------------------------------------------------------------------

    def init_replace_tags( self ):
        self.image_pat= re.compile( r'\<%image\(([^>]*)\|(\d+)\|(\d+)\|([^>]*)\)%\>' )

    def replace_nc_tags( self, text ):
        text= self.image_pat.sub( r'<img src="https://%s/\1" width="\2" height="\3" alt="\4" />' % self.media_url, text )
        return  text

    #--------------------------------------------------------------------------

    def parse_html( self, index ):

        item= self.load_json( index )
        if item is None:
            print( 'open error index=%d' % index )
            return  False

        print( '=========== %d' % index )
        #print( item )

        if self.debug_flag:
            print( '------------' )
            print( item['ibody'] )
            print( '------------' )

        #------------------------------------------- nucleus tags
        src_text= item['ibody']
        rep_text= self.replace_nc_tags( src_text )


        #------------------------------------------- html tags
        text= rep_text
        parser= TagParser( item['itime'], self.debug_flag, self.indexmap, self.datemap, self.account, self.config )
        parser.feed( text )
        item['replaced_html']= parser.get_text()
        item['media_list']= parser.get_media()

        if self.debug_flag:
            print( parser.get_text() )
            print( parser.get_media() )

        self.save_json( item )


    def f_single( self ):
        index= self.options['index']
        self.parse_html( index )

    def f_all( self ):
        for key in self.indexmap:
            index= int(key)
            self.parse_html( index )


#------------------------------------------------------------------------------

def usage():
    print( 'replacelink 2023 Hiroyuki Ogasawara' )
    print( 'usage: replacelink.py [<options>]' )
    print( 'options:' )
    print( '  --index <num>      single' )
    print( '  --all              all' )
    print( '  --debug' )
    print( '  --host <name>' )
    sys.exit( 0 )


def main( argv ):
    options= {
            'index': 0,
            'debug': False,
            'func': None,
            'host': 'default',
        }
    brun= False
    acount= len(argv)
    ai= 1
    while ai< acount:
        arg= argv[ai]
        if arg.startswith( '-' ):
            if arg == '--index':
                if ai+1 < acount:
                    ai+= 1
                    options['index']= int(argv[ai])
                    options['func']= 'f_single'
            elif arg == '--debug':
                options['debug']= True
            elif arg == '--all':
                options['func']= 'f_all'
            elif arg == '--host':
                if ai+1 < acount:
                    ai+= 1
                    options['host']= argv[ai]
            else:
                usage()
        else:
            usage()
        ai+= 1

    func_name= options['func']
    if func_name:
        rep= ReplaceLink( options )
        if hasattr( rep, func_name ):
            getattr( rep, func_name )()
        else:
            print( 'not found', options['func'] )
    else:
        usage()
    return  0


if __name__=='__main__':
    sys.exit( main( sys.argv ) )


