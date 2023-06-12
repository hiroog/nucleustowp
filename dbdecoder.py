# Table Decoder 2023/05 Hiroyuki Ogasawara
# vim:ts=4 sw=4 et:

import sys
import os
import re
import json


#------------------------------------------------------------------------------

# decoder= DBDecoder()
# decoder.decode_file( 'BACKUP.sql', 'nucleus_category' )
# decoder.save_json( 'category.json' )

class DBDecoder:

    def __init__( self ):
        self.title_list= None
        self.item_list= None

    #--------------------------------------------------------------------------

    def decode_tilte( self, titles ):
        title_list= []
        for title in titles.split( ',' ):
            title= title.strip( '` ' )
            title_list.append( title )
        return  title_list

    def decode_string( self, str_data ):
        scount= len(str_data)
        si= 0
        dest= ''
        while si< scount:
            ch= str_data[si]
            if ch == '\\':
                si+= 1
                nch= str_data[si]
                if nch == 'n':
                    ch= '\n'
                elif nch == 'r':
                    ch= '\r'
                else:
                    ch= nch
            dest+= ch
            si+= 1
        return  dest

    def decode_line( self, line, title_list ):
        ci= 1
        ccount= len(line)
        strmode= False
        word_list= []
        #text_list= []
        wd= ''
        while ci< ccount:
            ch= line[ci]
            if strmode:
                if ch == '\'':
                    ci+= 1
                    ch= line[ci]
                    if ch == '\'':
                        wd+= ch
                    else:
                        #text_list.append( wd )
                        word_list.append( self.decode_string(wd) )
                        wd= ''
                        strmode= False
                        if ch != ',':
                            ci-= 1
                else:
                    wd+= ch
            else:
                if ch == '\'':
                    strmode= True
                elif ch == ' ':
                    pass
                elif ch == ',' or ch == ';':
                    #text_list.append( None )
                    word_list.append( wd )
                    wd= ''
                elif ch == ')':
                    pass
                else:
                    wd+= ch
            ci+= 1
        dic= {}
        for title,word in zip(title_list,word_list):
            dic[title]= word
        dic['original']= line
        return  dic

    def decode_file( self, file_name, data_name ):
        print( 'decode_file: %s' % file_name )
        insert_pat= re.compile( r'^INSERT\s+INTO\s+`(\w+)`\s+\((.*)\)' )
        item_pat= re.compile( r'^\(' )
        title_list= []
        item_list= []
        step= 'skip'
        with open( file_name, 'r', encoding='utf-8' ) as fi:
            for line in fi:
                if step == 'skip':
                    pat= insert_pat.search( line )
                    if pat:
                        name= pat.group( 1 )
                        titles= pat.group( 2 )
                        if name == data_name:
                            title_list= self.decode_tilte( titles )
                            step= 'items'
                        continue
                elif step == 'items':
                    pat= item_pat.search( line )
                    if pat:
                        item= self.decode_line( line, title_list )
                        item_list.append( item )
                        continue
                    pat= insert_pat.search( line )
                    if pat:
                        name= pat.group( 1 )
                        if name != data_name:
                            step= 'end'
                        continue
                elif step == 'end':
                    break

        print( 'decode_count=%d' % len(item_list) )
        self.title_list= title_list
        self.item_list= item_list

    def save_json( self, save_file ):
        with open( save_file, 'w', encoding='utf-8' ) as fo:
            fo.write( json.dumps( self.item_list, sort_keys=True, indent=4, ensure_ascii=False ) )


#------------------------------------------------------------------------------

class Decoder:

    def __init__( self, options ):
        self.options= options
        self.blog= options['blog']
        for folder_name in [ 'item', 'category', 'comment' ]:
            if not os.path.exists( folder_name ):
                os.mkdir( folder_name )

    #--------------------------------------------------------------------------

    def save_json( self, file_name, data ):
        bak_name= file_name + '.bak'
        if os.path.exists( bak_name ):
            os.remove( bak_name )
        if os.path.exists( file_name ):
            os.rename( file_name, bak_name )
        with open( file_name, 'w', encoding='utf-8' ) as fo:
            fo.write( json.dumps( data, sort_keys=True, indent=4 ) )

    #--------------------------------------------------------------------------

    def get_blog_filter( self, item_list, key ):
        new_list= []
        for item in item_list:
            blog= int(item[key])
            if blog == self.blog:
                new_list.append( item )
        return  new_list

    #--------------------------------------------------------------------------

    def decode_item( self, file_name ):
        dec= DBDecoder()
        dec.decode_file( file_name, 'nucleus_item' )
        item_list= self.get_blog_filter( dec.item_list, 'iblog' )

        print( 'item_count=%d' % len(item_list) )

        indexdb= {}
        datedb= {}
        for item in item_list:
            itime= item['itime']
            idate= itime[:10]
            inumber= int(item['inumber'])
            indexdb[inumber]= itime
            if idate not in datedb:
                datedb[idate]= []
            datedb[idate].append( inumber )

        print( 'indexdb=%d' % len(indexdb) )
        print( 'datedb=%d' % len(datedb) )

        self.save_json( 'item/index.json', indexdb )
        self.save_json( 'item/date.json', datedb )

        for item in item_list:
            save_name= 'item/%s.json' % item['inumber']
            self.save_json( save_name, item )

    #--------------------------------------------------------------------------

    def decode_category( self, file_name ):
        dec= DBDecoder()
        dec.decode_file( file_name, 'nucleus_category' )
        item_list= self.get_blog_filter( dec.item_list, 'cblog' )
        for item in item_list:
            item['slug']= 'cat%d' % int(item['catid'])
        self.save_json( 'category/category.json', item_list )

    #--------------------------------------------------------------------------

    def decode_comment( self, file_name ):
        dec= DBDecoder()
        dec.decode_file( file_name, 'nucleus_comment' )
        item_list= self.get_blog_filter( dec.item_list, 'cblog' )

        print( 'comment_count=%d' % len(item_list) )

        index_list= []
        for item in item_list:
            cnumber= int(item['cnumber'])
            index_list.append( cnumber )

        print( 'index count=%d' % len(index_list) )
        self.save_json( 'comment/index.json', index_list )

        for item in item_list:
            save_name= 'comment/%s.json' % item['cnumber']
            self.save_json( save_name, item )



#------------------------------------------------------------------------------

def usage():
    print( 'dbdecoder 2023 Hiroyuki Ogasawara' )
    print( 'usage: dbdecoder.py --sql <file.sql> [<options>..]' )
    print( 'options:' )
    print( '  --sql <file.sql>' )
    print( '  --all' )
    print( '  --nc_item          nucleus item' )
    print( '  --nc_category      nucleus category' )
    print( '  --nc_comment       nucleus comment' )
    print( '  --blog <num>' )
    print( '  --parse <name>' )
    print( '  --save <output_name>' )
    print( 'ex. dbdecoder.py --json --map' )
    sys.exit( 0 )


def main( argv ):
    options= {
            'nc_item': False,
            'nc_category': False,
            'nc_comment': False,
            'parse': None,
            'sql': None,
            'save': 'output.json',
            'blog': 1,
        }
    brun= False
    brun2= False
    acount= len(argv)
    ai= 1
    while ai< acount:
        arg= argv[ai]
        if arg.startswith( '-' ):
            if arg == '--nc_item':
                options['nc_item']= True
                brun= True
            elif arg == '--nc_category':
                options['nc_category']= True
                brun= True
            elif arg == '--nc_comment':
                options['nc_comment']= True
                brun= True
            elif arg == '--all':
                options['nc_item']= True
                options['nc_category']= True
                options['nc_comment']= True
                brun= True
            elif arg == '--blog':
                if ai+1 < acount:
                    ai+= 1
                    options['blog']= int(argv[ai])
            elif arg == '--parse':
                if ai+1 < acount:
                    ai+= 1
                    options['parse']= argv[ai]
                    brun2= True
            elif arg == '--save':
                if ai+1 < acount:
                    ai+= 1
                    options['save']= argv[ai]
            elif arg == '--sql':
                if ai+1 < acount:
                    ai+= 1
                    options['sql']= argv[ai]
            else:
                usage()
        else:
            usage()
        ai+= 1

    if options['sql'] is None:
        usage()

    if brun2:
        decoder= DBDecoder()
        decoder.decode_file( options['sql'], options['parse'] )
        decoder.save_json( options['save'] )
    elif brun:
        decoder= Decoder( options )
        if options['nc_category']:
            decoder.decode_category( options['sql'] )
        if options['nc_item']:
            decoder.decode_item( options['sql'] )
        if options['nc_comment']:
            decoder.decode_comment( options['sql'] )
    else:
        usage()
    return  0


if __name__=='__main__':
    sys.exit( main( sys.argv ) )


