import sys

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst

class GstTracerLineParsingException(Exception): pass

class GstTracerLine(object):
    def __init__(self, line):
        self.line = line
        tokens = line.split()
        if len(tokens) < 8:
            raise GstTracerLineParsingException
        if 'TRACE' not in tokens[3]:
            raise GstTracerLineParsingException
        if 'GST_TRACER' != tokens[6]:
            raise GstTracerLineParsingException

        self.time = tokens[0]

        #FIXME some structures fail parsing
        self.structure = Gst.Structure.from_string(' '.join(tokens[8:]))[0]

    def get_thread(self):
        return self.structure.get_value('thread-id')

    def is_query(self):
        return self.structure and self.structure.get_name() == 'query'

    # QUERY RELATED FUNCTIONS
    def is_query_type(self, name):
        return self.structure.get_value('name') == name

    def query_between_elements(self):
        return self.structure.get_value('elem-ix') != 4294967295 and \
               self.structure.get_value('peer-elem-ix') != 4294967295

    def is_post_query(self):
        return self.structure.has_field('res')

    # END OF QUERY RELATED FUNCTIONS

    def __str__(self):
        return self.line

class GstCapsQueryTree(object):
    def __init__(self, root):
        self.root = root
        self.current = root

    def add_node(self, node):
        if node.queryline.is_post_query():
            print 'Post query - closing: ', self.current.queryline
#            assert self.current.queryline == node.queryline
            self.current.queryline = node.queryline
            self.current.close()
            self.current = self.current.parent
        else:
            print 'Pre query'
            self.current.add_child(node)
            self.current = node

    def is_closed(self):
        return self.current == None

class GstCapsQueryTreeNode(object):
    def __init__(self, queryline):
        self.children = []
        self.state = 'open'
        self.queryline = queryline
        self.parent = None

    def close(self):
        self.state = 'closed'

    def add_child(self, node):
        self.children.append(node)
        node.parent = self

def process_file(input_file):

    # Each thread will maintain the current GstCapsQueryTree running in it
    # until it is closed, then it is removed
    threads = {}
    query_trees = []

    with open(input_file, 'r') as f:
        for line in f:
            try:
                tracer_line = GstTracerLine(line)
            except GstTracerLineParsingException:
                continue

            if not tracer_line.is_query(): continue
            if not tracer_line.is_query_type('caps'): continue
            if not tracer_line.query_between_elements(): continue

            thread = tracer_line.get_thread()
            print '=============================================================================='
            print threads
            print 'Thread:', thread
            print 'Line:', tracer_line
            if thread in threads:
                tree = threads[thread]
                tree.add_node(GstCapsQueryTreeNode(tracer_line))
                if tree.is_closed():
                    query_trees.append(tree)
                    del threads[thread]
            else:
                print 'New root'
                tree = GstCapsQueryTree(GstCapsQueryTreeNode(tracer_line))
                threads[thread] = tree
            print

    print threads
    return query_trees


if __name__ == '__main__':
    Gst.init()

    input_file = sys.argv[1]

    r = process_file (input_file)
    print len(r)
