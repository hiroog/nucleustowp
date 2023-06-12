# wpost.py 2023/05 Hiroyuki Ogasawara
# vim:ts=4 sw=4 et:

import sys
import os
import requests
import base64
import json
import re


class Poster:

    EXT_MAP= {
            '.jpg'  : 'jpeg',
            '.jpeg' : 'jpeg',
            '.gif'  : 'gif',
            '.png'  : 'png',
        }

    def __init__( self, options ):
        self.options= options
        self.update_flag= options['update']
        self.verify= options['verify']
        self.website_url= None
        self.headers= None
        self.load_settings()
        self.set_account( options['account'] )
        self.date_pat= re.compile( r'(\d\d\d\d)-(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d)' )
        self.category_map= None
        self.local_media_path= self.config['local_media_path']

    def load_settings( self ):
        settings_file= 'settings.json'
        with open( settings_file, 'r', encoding='utf-8') as fi:
            self.settings= json.loads( fi.read() )
            self.config= self.settings['config']
            return  True
        print( 'open error: %s' % settings_file )
        sys.exit( 1 )
        return  False

    def set_account( self, name ):
        if name in self.settings:
            self.set_account_0( self.settings[name] )
            return  True
        print( 'account error: %s' % name )
        sys.exit( 1 )
        return  False

    def set_account_0( self, account ):
        self.website_url= account['url']
        username= account['user']
        password= account['pass']
        auth_string = '{}:{}'.format( username, password )
        auth_string_b64 = base64.b64encode( auth_string.encode('utf-8') ).decode('utf-8')
        self.headers = {
            'Authorization' : 'Basic {}'.format( auth_string_b64 ),
            'Content-Type'  : 'application/json; charset=UTF-8',
        }

    def make_slug( self, item ):
        index= int( item['inumber'] )
        # 0000-00-00 00:00:00
        pat= self.date_pat.search( item['itime'] )
        if pat:
            year= pat.group( 1 )
            month= pat.group( 2 )
            day= pat.group( 3 )
            '%04d/%02d/%02d' % (year,month,day)


    # call_api( 'GET', 'posts', { 'per_page': 20 }, None, None )
    def call_api( self, method, api_name, args, data= None, ctype= None ):
        api_base_path = '/wp-json/wp/v2'
        url= '%s%s/%s' % (self.website_url, api_base_path, api_name)

        print( 'CALL %s %s <%s>' % (method,url,str(args)) )

        headers= self.headers.copy()
        if ctype:
            headers.update( ctype )
            print( '###', headers )

            if method == 'GET':
                response= requests.get( url, headers=headers, params=args, verify=self.verify )
            elif method == 'POST':
                response= requests.post( url, data=data, headers=headers, params=args, verify=self.verify )
            else:
                print( 'method error', method )
                return  None

        else:
            print( '###', headers )

            if method == 'GET':
                response= requests.get( url, headers=headers, params=args, verify=self.verify )
            elif method == 'POST':
                response= requests.post( url, json=data, headers=headers, params=args, verify=self.verify )
            else:
                print( 'method error', method )
                return  None


        if response.status_code >= 200 and response.status_code < 300:
            print( 'API CALL SUCCESS %d' % response.status_code )
            json_obj= response.json()
            if 'id' in json_obj:
                print( 'Post Item ID: %d' % json_obj['id'] )
            return  json_obj
        else:
            print( 'API CALL ERROR: %d' % response.status_code )
            #with open( 'error.txt', 'w', encoding='utf-8' ) as fo:
            #    fo.write( response.text )
            print( response.text )
            print( response.json()['message'] )
            print( 'DATA ======> ', data )
        return  None


    #--------------------------------------------------------------------------

    def find_item( self, index ):
        result= self.call_api( 'GET', 'posts', { 'slug':'n%d' % index } )
        #print( result )
        if len(result) > 0:
            return  result[0]
        return  None


    def post_item( self, item ):
        api_name= 'posts'
        index= int( item['inumber'] )
        wp_item= self.find_item( index )
        if wp_item:
            if not self.update_flag:
                print( 'SKip: already exists: %d' % index )
                return  'Skip'
            wp_index= wp_item['id']
            api_name= 'posts/%d' % wp_index

        i_body= item['replaced_html']
        i_date= item['itime'].replace( ' ', 'T' )
        i_title= item['ititle']
        i_slug= 'n%d' % index
        i_cat= item['icat']
        if i_cat in self.category_map:
            ret= self.category_map[i_cat]
            wp_num= ret['wp_index']
            i_categories= [wp_num]
        else:
            i_categories= [1]

        post_data = {
            'title': i_title,
            'content': i_body,
            'date': i_date,
            'slug' : i_slug,
            'categories': i_categories,
            'status': 'publish',  # 'publish' or 'draft'
        }
        #print( '======================' )
        #print( post_data )
        #print( '======================' )
        ret= self.call_api( 'POST', api_name, None, post_data )
        if ret:
            post_id= ret['id']
            media_list= item['media_list']
            for media_name in media_list:
                self.send_media( media_name, post_id, i_date )
        return  ret


    def f_get_item( self, options ):
        index= options['index']
        result= self.call_api( 'GET', 'posts', { 'slug':'n%d' % index } )
        for item in result:
            print( '======= %d ========' % index )
            for key in item:
                val= item[key]
                if type(val) is dict:
                    for key2 in val:
                        val2= val[key2]
                        print( '  %s : "%s"' % (key2, str(val2) ) )
                else:
                    print( '%s : "%s"' % (key, str(val) ) )

    def post_single( self, index ):
        print( 'POST index=%d' % index )
        file_name= 'item2/%d.json' % index
        with open( file_name, 'r', encoding='utf-8' ) as fi:
            obj= json.loads( fi.read() )
            ret= self.post_item( obj )
            if ret is None:
                print( 'ERROR =====>', obj )
            return  ret
        return  None


    def f_post_item( self, options ):
        self.category_map= self.load_category_map()
        self.post_single( options['index'] )

    def f_post_all( self, options ):
        self.category_map= self.load_category_map()
        with open( 'item/index.json', 'r', encoding='utf-8' ) as fi:
            obj= json.loads( fi.read() )
        for key in obj:
            index= int(key)
            ret= self.post_single( index )
            #print( ret )
            if ret == 'Skip':
                continue
            if ret is None:
                break


    def f_list_item( self, options ):
        index= options['index']
        result= self.call_api( 'GET', 'posts', {} )
        print( '---------------------' )
        for item in result:
            if False:
                print( '**************' )
                for key in item:
                    val= item[key]
                    print( '%s : "%s"' % (key, str(val) ) )
            i_id=   item['id']
            i_date= item['date']
            i_slug= item['slug']
            i_link= item['link']
            i_title= item['title']['rendered']
            print( '%4d %s %s "%s"' % (i_id,i_date,i_link,i_title) )

    #--------------------------------------------------------------------------
    
    def load_category_src( self ):
        file_name= 'category/category.json'
        with open( file_name, 'r', encoding='utf-8' ) as fi:
            return  json.loads( fi.read() )
        return  None

    def load_category_map( self ):
        file_name= 'category/category2.json'
        if os.path.exists( file_name ):
            with open( file_name, 'r', encoding='utf-8' ) as fi:
                return  json.loads( fi.read() )
        print( 'category file "%s" not found. please execute with --save_category_map command' % file_name )
        sys.exit( 1 )
        return  None

    def save_category_map( self, cat_map ):
        file_name= 'category/category2.json'
        with open( file_name, 'w', encoding='utf-8' ) as fo:
            fo.write( json.dumps( cat_map, sort_keys=True, indent=4 ) )

    def f_list_categories( self, options ):
        result= self.call_api( 'GET', 'categories', {'per_page':50} )
        print( '---------------------' )
        for item in result:
            if False:
                print( '**************' )
                for key in item:
                    val= item[key]
                    print( '%s : "%s"' % (key, str(val) ) )
            print( '%2d p%d %-14s %-24s   %s' % (item['id'],item['parent'],item['slug'],item['name'],item['description']) )

    def find_category( self, slug ):
        ret= self.call_api( 'GET', 'categories', { 'slug':slug } )
        if ret:
            return  ret[0]
        return  None

    def f_upload_categories( self, options ):
        cat_list= self.load_category_src()
        for cat in cat_list:
            if int(cat['cblog']) == 1:
                print( cat['cname'] )
                slug= cat['slug']
                api_name= 'categories'
                ret= self.find_category( slug )
                if ret:
                    wp_index= int(ret['id'])
                    api_name= 'categories/%d' % wp_index
                data= {
                    'name': cat['cname'],
                    'description': cat['cdesc'],
                    'slug': cat['slug'],
                    }
                result= self.call_api( 'POST', api_name, {}, data )
        print( 'upload %d categories' % len(cat_list) )

    def f_save_category_map( self, options ):
        cat_list= self.load_category_src()
        category_map= {}
        for cat in cat_list:
            index= cat['catid']
            slug= cat['slug']
            if int(cat['cblog']) == 1:
                ret= self.find_category( slug )
                wp_index= 0
                if ret:
                    wp_index= int(ret['id'])
                cat['wp_index']= wp_index
                category_map[index]= cat
        self.save_category_map( category_map )

    #--------------------------------------------------------------------------

    def f_list_media( self, options ):
        result= self.call_api( 'GET', 'media', {'per_page':50} )
        print( '---------------------' )
        for item in result:
            if False:
                print( '**************' )
                for key in item:
                    val= item[key]
                    print( '%s : "%s"' % (key, str(val) ) )
            print( '%3d %-24s  %s' % (item['id'],item['slug'],item['guid']['rendered']) )

    def find_media( self, media_name ):
        slug_name,_= os.path.splitext( os.path.basename(media_name).lower() )
        result= self.call_api( 'GET', 'media', {'slug':slug_name} )
        if result:
            return  result[0]
        return  None

    def f_get_media( self, options ):
        media_name= options['media']
        ret= self.find_media( media_name )
        if ret:
            #print( ret )
            for key in ret:
                val= ret[key]
                print( '%s  : %s' % (key,str(val)) )

    def send_media( self, file_name, post_id= -1, date= None ):
        ret= self.find_media( file_name )
        api_name= 'media'
        if ret:
            update_flag= self.update_flag
            update_flag= False
            if not update_flag:
                print( 'Already Exists', file_name )
                return
            wp_index= ret['id']
            api_name= 'media/%d' % wp_index
        args= { 'comment_status': 'closed' }
        if date:
            args['date']= date
        if post_id >= 0:
            args['post']= post_id
        _,ext= os.path.splitext( file_name.lower() )
        ctype= {}
        if ext in self.EXT_MAP:
            ctype['Content-Type']= 'image/' + self.EXT_MAP[ext]
        ctype['Content-Disposition']= 'attachment; filename="%s"' % file_name
        file_path= os.path.join( self.local_media_path, file_name )
        with open( file_path, 'rb' ) as fi:
            post_data= fi.read()
        ret= self.call_api( 'POST', api_name, args, post_data, ctype )
        if ret:
            image_id= ret['id']
            print( 'send image id=%d %s' % (image_id, file_name) )

    def f_send_media( self, options ):
        media_name= options['media']
        self.send_media( media_name )

    #--------------------------------------------------------------------------

    def f_list_comment( self, options ):
        result= self.call_api( 'GET', 'comments', {'per_page':50} )
        print( '---------------------' )
        for item in result:
            if True:
                print( '**************' )
                for key in item:
                    val= item[key]
                    print( '%s : "%s"' % (key, str(val) ) )
            print( '%3d %4d %-20s %s' % (item['id'],item['post'],item['date'],item['content']) )

    # item id -> wp-index から comment list を取り date でマッチさせる
    def find_comment( self, wp_index, date ):
        result= self.call_api( 'GET', 'comments', { 'post': wp_index, 'per_page':100 } )
        if result:
            for ret in result:
                comment_date= ret['date']
                if comment_date == date:
                    comment_id= ret['id']
                    return  comment_id
        return  0

    def post_comment( self, item ):
        api_name= 'comments'
        index= int( item['citem'] )
        wp_item= self.find_item( index )
        if wp_item:
            wp_index= wp_item['id']
            date= item['ctime'].replace( ' ', 'T' )
            comment_id= self.find_comment( wp_index, date )
            if comment_id > 0:
                api_name= 'comments/%d' % comment_id
        else:
            print( 'Item not found index=%d' % index )
            return  None

        args= {}
        author= int(item['cmember'])
        if author == 0:
            self.set_account( self.options['account'] + 'guest' )
            args['status']= 'approved'
            print( 'SET GUEST' )
        elif author == 1:
            self.set_account( self.options['account'] )
            print( 'SET USER=1' )
        else:
            print( 'USER ERROR', author )

        post_data = {
            'content': item['cbody'],
            'date': item['ctime'].replace( ' ', 'T' ),
            'post' : wp_index,
            'author_name' : item['cuser'],
        }
        ret= self.call_api( 'POST', api_name, args, post_data )
        return  ret

    def f_post_comment( self, options ):
        index= options['index']
        file_name= 'comment/%d.json' % index
        with open( file_name, 'r', encoding='utf-8' ) as fi:
            obj= json.loads( fi.read() )
        self.post_comment( obj )


    def f_comment_all( self, options ):
        file_name= 'comment/index.json'
        with open( file_name, 'r', encoding='utf-8' ) as fi:
            num_list= json.loads( fi.read() )
        for num in num_list:
            print( '######### POST Comment index=%d' % num )
            file_name= 'comment/%d.json' % num
            with open( file_name, 'r', encoding='utf-8' ) as fi:
                obj= json.loads( fi.read() )
            ret= self.post_comment( obj )
            if ret is None:
                break





#------------------------------------------------------------------------------
#
#  1.
#    edit settings.json
#
#  2.
#    python dbdecoder.py --all
#
#  3.
#    python replacelink.py --all --host NAME
#
#  4.
#    python wdpost.py --upload_categories   (upload category/category.json to wordpress)
#    python wdpost.py --save_category_map   (save to category/category2.json)
#    python wdpost.py --post_all --update
#    python wdpost.py --comment_all
#
#------------------------------------------------------------------------------



def usage():
    print( 'wdpost 2023/05 Hiroyuki Ogasawara' )
    print( 'usage: wpost [options]' )
    print( '--index <num>' )
    print( '--host <name>' )
    print( '--update' )
    print( '--debug' )
    print( '--post_item         (req --index n, opt --update)' )
    print( '--list_item' )
    print( '--get_item          (req --index n)' )
    print( '--post_all          (opt --update)' )
    print( '--list_categories' )
    print( '--upload_categories' )
    print( '--save_category_map' )
    print( '--list_media' )
    print( '--media <name>' )
    print( '--get_media         (req --media n)' )
    print( '--send_media        (req --media n)' )
    print( '--list_comment' )
    print( '--post_comment      (req --index n)' )
    print( '--comment_all' )
    sys.exit( 0 )



def main( argv ):
    options= {
            'index': 0,
            'func': None,
            'update': False,
            'media': None,
            'account': 'default',
            'verify': True,
        }
    acount= len(argv)
    ai= 1
    while ai< acount:
        arg= argv[ai]
        if arg.startswith( '-' ):
            if arg == '--index':
                if ai+1 < acount:
                    ai+= 1
                    options['index']= int(argv[ai])
            elif arg == '--host' or arg == '--account':
                if ai+1 < acount:
                    ai+= 1
                    options['account']= argv[ai]
            elif arg == '--post_item':
                options['func']= 'f_post_item'
            elif arg == '--list_item':
                options['func']= 'f_list_item'
            elif arg == '--get_item':
                options['func']= 'f_get_item'
            elif arg == '--post_all':
                options['func']= 'f_post_all'
            elif arg == '--update':
                options['update']= True
            elif arg == '--debug':
                options['verify']= False
            elif arg == '--list_categories':
                options['func']= 'f_list_categories'
            elif arg == '--upload_categories':
                options['func']= 'f_upload_categories'
            elif arg == '--save_category_map':
                options['func']= 'f_save_category_map'
            elif arg == '--list_media':
                options['func']= 'f_list_media'
            elif arg == '--media':
                if ai+1 < acount:
                    ai+= 1
                    options['media']= argv[ai]
            elif arg == '--get_media':
                options['func']= 'f_get_media'
            elif arg == '--send_media':
                options['func']= 'f_send_media'
            elif arg == '--list_comment':
                options['func']= 'f_list_comment'
            elif arg == '--post_comment':
                options['func']= 'f_post_comment'
            elif arg == '--comment_all':
                options['func']= 'f_comment_all'
            else:
                usage()
        else:
            usage()
        ai+= 1

    func= options['func']
    if func:
        poster= Poster( options )
        if hasattr( poster, func ):
            getattr( poster, func )( options )
        else:
            print( '%s not found' % func )
            usage()
    else:
        usage()

    return  0



if __name__=='__main__':
    sys.exit( main( sys.argv ) )


