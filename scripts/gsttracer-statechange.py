import sys

class ElementStateChange(object):
    def __init__(self, initial_state, final_state, transition_start_ts, transition_end_ts):
        self.initial_state = initial_state
        self.final_state = final_state
        self.transition_start_ts = transition_start_ts
        self.transition_end_ts = transition_end_ts

    def __str__(self):
        return '%s -> %s : %d' % (self.initial_state, self.final_state, (self.transition_end_ts - self.transition_start_ts))


class ElementStateChangeTiming(object):
    def __init__(self, ptr, element, ts):
        self.ptr = ptr
        self.element = element
        self.ts = ts
        self.state = 'null'
        self.pending_state = None
        self.transition_start = None
        self.transitions = []

    def start_state_change(self, ts, initial_state, final_state):
        assert self.state == initial_state, '%s: %s != %s' % (self.element, self.state, initial_state)
        assert self.pending_state == None
        self.pending_state = final_state
        self.transition_start = ts

    def finish_state_change(self, ts, initial_state, final_state, result):
        if result != 'failure':
            assert final_state == self.pending_state
            self.state = final_state
            self.transitions.append(ElementStateChange (initial_state, final_state, self.transition_start, ts))
            self.pending_state = None
            self.transition_start = None



def parse_entry(entry):
    tokens = entry.split('$')
    timestamp = int(tokens[0])
    event = tokens[1]
    ptr = tokens[2]
    element = tokens[3][1:-1] #remove < > around element name

    return timestamp, event, ptr, element, tokens[4:]

def process_file(input_file):
    old_elements = []
    elements = {}

    with open(input_file, 'r') as f:
        for line in f:
            # Get the last token
            entry = line.split(' ')[-1].strip()

            try:
                ts, event, ptr, element, data = parse_entry(entry)
            except:
                #TODO use a proper exception
                continue

            if event == 'element-new':
                data = ElementStateChangeTiming(ptr, element, ts)
                if ptr in elements:
                    old_elements.append(elements[ptr])
                elements[ptr] = data
            elif event == 'element-state-change-pre':
                elements[ptr].start_state_change(ts, data[0], data[1])
            elif event == 'element-state-change-post':
                elements[ptr].finish_state_change(ts, data[0], data[1], data[2])

    return sorted(old_elements + elements.values(), key=lambda x: x.ts)

def output_html_timeline_chart(elements):

    maxtime = max([x.ts for x in elements])
    for e in elements:
        if e.transitions:
            maxtime = max(maxtime, max([x.transition_end_ts for x in [t for t in e.transitions]]))

    html = """
<html>
  <head>
    <script type="text/javascript" src="https://www.google.com/jsapi"></script>
    <script type="text/javascript">
      google.load("visualization", "1.1", {packages:["timeline"]});
      google.setOnLoadCallback(drawChart);

      function drawChart() {
        var container = document.getElementById('timeline-tooltip');
        var chart = new google.visualization.Timeline(container);
        var dataTable = new google.visualization.DataTable();

        dataTable.addColumn({ type: 'string', id: 'Element' });
        dataTable.addColumn({ type: 'string', id: 'dummy bar label' });
        dataTable.addColumn({ type: 'string', role: 'tooltip' });
        dataTable.addColumn({ type: 'number', id: 'Start' });
        dataTable.addColumn({ type: 'number', id: 'End' });
        dataTable.addRows([
%(data)s
        ]);

        chart.draw(dataTable);
      }
    </script>
  </head>
  <body>
    <div id="timeline-tooltip" style="height: 1080px;"></div>
  </body>
</html>
    """
    data = []
    for e in elements:
        data.append("['%s', '%s', '%s', %d, %d]" % (e.element, 'null', e.ptr, e.ts, maxtime))

    return html % {'data': ',\n'.join(data)}

if __name__ == '__main__':
    input_file = sys.argv[1]

    data = process_file (input_file)

    output_mode = 'timeline'
    if output_mode == 'timeline':
        print output_html_timeline_chart(data)
    else:
        for e in sorted(old_elements + elements.values(), key=lambda x: x.ts):
            print e.element
            print '  Created at: %d' % e.ts
            for t in e.transitions:
                print '  Transition: %s' % str(t)
