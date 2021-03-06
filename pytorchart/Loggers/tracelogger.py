from visdom import Visdom
from .style_utils import _def_opts, _def_layout, _spec, lyout_spec
import pickle, math, pprint
from ..utils import deep_merge
from .base import BaseLogger

_nan = float('NaN')


class TraceLogger(BaseLogger):
    """
    Logging arbitrary data by keys at runtime to a metering operation.

    TraceLogger has the same idea as tnt.VisdomLogger, but with more access to
    plotly properties directly, with the downside of being less flexible. Also,
    it bypasses the visdom.scatter interface, and directly sends json data,
    so a few things which are rather difficult to do like specifing lines with
    a certain color and line style.

    Though this is not meant to be used directly, it can be by all means:

    :Examples:


    """
    def __init__(self,
                 *args,
                 opts={},
                 vis=None,
                 legend=[],
                 env=None,
                 port=8097,
                 **kwargs):
        super(TraceLogger, self).__init__()
        self._legend = legend
        self._port  = port
        self._win   = None
        self._env   = env if env is not None else 'main'

        self._opts   = deep_merge(_def_opts, opts.get('opts', {}))
        self._layout = deep_merge(_def_layout, opts.get('layout', {}))
        self._layout['title'] = opts.get('title', '').capitalize()

        self._lines  = self._init_lines(legend, opts.get('data', {}))
        self._viz    = vis if isinstance(vis, Visdom) else Visdom(port=port)
        self._traces = [0] * len(self._lines)
        self._debug = kwargs.get('debug', False)
        if self._debug is True:
            print(self._opts)

    @property
    def viz(self):
        """
        retrieves the Visdom Object

        :return: visom.Visdom Object
        """
        return self._viz

    def save(self, path):
        """
        saves self, and saves the visdom enviornment.

        :param path: valid filepath
        :return: None
        """
        super(BaseLogger, self).save(path)
        return self._viz.save([self._env])

    @classmethod
    def _check_trace(cls, opts, pre='', mp_spec=_spec):
        """

        :param opts:
        :param pre:
        :param mp_spec:
        :return:
        """
        _opts = {}
        for k, value in opts.items():
            fk = k if pre == '' else pre + '.' + k
            if isinstance(value, dict):
                _opts[k] = cls._check_trace(value, fk)
            else:
                spec = mp_spec.get(fk, None)
                if isinstance(spec, list) and value in spec:
                    _opts[k] = value
                elif isinstance(spec, type) and isinstance(value, spec):
                    _opts[k] = value
        return _opts

    @classmethod
    def _init_lines(cls, titles, opts):
        """

        :param titles:
        :param opts:
        :return:

        Usage :
             {'line1':{
                'name': '1',
                'type': 'scatter',
                  'marker': {'size': 10,
                             'symbol': 'dot',
                             'line': {'width': 0.5, 'color': '#000000'}},
                  'mode': 'lines'}}
        """
        lines = []
        for title in titles:
            trace_style = opts.get(title, {})
            opts_dict = cls._check_trace(trace_style, mp_spec=_spec)
            # todo required keys
            opts_dict['type'] = 'scatter'
            opts_dict['mode'] = 'lines'
            lines.append(opts_dict)
        return lines

    @property
    def _base_data(self):
        return {
            'win': self._win,
            'eid': self._env,
            'layout': self._layout,
            'opts': self._opts,
        }

    def _create_trace(self, X, Y, first=False):
        """

        :param X:
        :param Y:
        :return:
        """
        assert len(X) == len(Y), 'X and Y inputs not same size'
        data_to_send, data = None, []

        for i, (x, y) in enumerate(zip(X, Y)):
            if y is None or math.isnan(y):
                y = None
                if self._win is not None:
                    continue
            line_dict = self._lines[i].copy()
            line_dict['x'] = [x]
            line_dict['y'] = [y]
            data.append(line_dict)

        if data != []:
            data_to_send = self._base_data
            data_to_send['data'] = data

        return data_to_send

    def log(self, X, Y):
        """
        Same interface as torchnet.log(), applies metadata to the X,Y Values,
        and sends them to the visdom plot.

        :param X: list of integers - X-axis values of size self.num_lines
        :param Y: list of integers - X-axis values of size self.num_lines
        :return: None
        """
        ds = self._create_trace(X, Y)

        if self._win is not None and ds is not None:
            ds['append'] = True
            ds['win'] = self._win
            self._viz._send(ds, endpoint='update')

        elif self._win is None and ds is not None:
            print('starting plot ', self._layout['title'], len(ds['data']), self._legend)
            self._win = self._viz._send(ds, endpoint='events')

    def __repr__(self):
        st = '\n'
        for spec in self._lines:
            st += _unwrap(spec) + '\n'
        return st


def _unwrap(dict_, pre=''):
    st = ''
    for k, v in dict_.items():
        if isinstance(v, dict):
            st += pre + k + ': \n' + _unwrap(v, pre + ' '*3)
        else:
            st += pre + k + ': ' + str(v) + '\n'
    return st


