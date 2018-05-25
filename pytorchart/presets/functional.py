import torch
import torch.nn as nn
from pytorchart.Loggers.style_utils import _spec
from inspect import signature, _empty, Parameter
import pprint
import random

_index = ['layer', 'name', 'data', 'func']


def _modules_requiring_grads():
    """
    Generate a list of types that have weights, and therefore will get Grads.
    It is a bit hacky,
    :return:
    """
    has_grad = []
    for k, cls in nn.__dict__.items():
        required = 0
        if not isinstance(cls, type):
            continue
        ds = signature(cls)
        # conver RNN and container case
        if issubclass(cls, nn.RNNBase) or issubclass(cls, nn.Container):
            has_grad.append(cls)
            continue
        for _k, param in ds.parameters.items():
            if param.default == _empty and param.kind != Parameter.VAR_POSITIONAL:
                required += 1
        args = [i+1 for i in range(required)]
        try:
            inst = cls(*args)
            # for most modules its in weight
            if hasattr(inst, 'weight'):
                has_grad.append(cls)
        except Exception as err:
            print('cannot inspect', cls.__name__, required, str(err))
    # [print(x) for x in has_grad]
    return has_grad


IGrad = _modules_requiring_grads()
###########################################################


def get_in(o, kys, d=None):
    ob = o.copy()
    while ob and kys:
        k = kys.pop(0)
        ob = ob.get(k, None)
    if ob is None:
        return d
    return ob


def identity(*x):
    return x


def summarize(model, fn=identity):
    res = []
    for key, module in model._modules.items():
        if type(module) in [
            nn.Container,
            nn.Sequential,
            nn.ModuleList,
            # nn.Module,
        ]:
            res += summarize(module, fn=fn)
        elif any(module._modules):
            res += summarize(module, fn=fn)
        elif 'weight' in module._parameters:
            summary = fn(key, module)
            # print(key, summary)
            if summary is not None:
                res.append(summary)
    return res


#############################
def _grad_wrt_weight(module, grad_in):
    m = list(module._parameters['weight'].size())
    if type(module) in [nn.Linear]:
        m = m[::-1]
    if grad_in is not None:
        for g in grad_in:
            if g is not None and list(g.size()) == m:
                return g.data


def grad_mean_snr(module, grad_in, grad_out):
    m = module._parameters['weight'].data.max()
    g_wrt_w_data = _grad_wrt_weight(module, grad_in)
    n = g_wrt_w_data / m
    return n.mean()


def grad_std(module, grad_in, grad_out):
    return _grad_wrt_weight(module, grad_in).std()


def gen_grad_wrt_w(fn):
    def hook(m, i, o):
        return fn(_grad_wrt_weight(m, i))
    return hook


def gen_module_wght(fn):
    def hook(m, i, o):
        return fn(m._parameters['weight'].data)
    return hook


def grad_mean(module, grad_in, grad_out):
    return _grad_wrt_weight(module, grad_in).mean()


def grad_norm(module, grad_in, grad_out):
    return _grad_wrt_weight(module, grad_in).norm()


def has_grad(name, module_type):
    if module_type in IGrad:
        return name
    return None


#############################
_grad_layers = lambda name, m: name if type(m) in IGrad else None


_def_plot = {
    'type': 'line',
    'opts': {'layout': {'yaxis': {'type': 'log', 'autorange': True}}}
}

fspecs = \
    {'grad_norms':
        {'doc': " common thing to track about the gradient, ",
         'layer': _grad_layers,
         'data': 'backward',
         'name': 'grad_norm',
         'func': [grad_mean, grad_norm],
         'same': {'layer': 'line.color', 'func': 'line.dash'}},
     'snr':
         {'doc': " Tishby et al. ",
          'layer': _grad_layers,
          'data': 'backward',
          'name': 'std_meter',
          'func': [grad_std, grad_mean_snr],
          'same': {'layer': 'line.color', 'func': 'line.dash'}}
     }


class LayerLegend(object):
    def __init__(self):
        self.legend = {}

    def color_for(self, layer):
        if layer not in self.legend:
            self.legend[layer] = self._gen_color()
        return self.legend[layer]

    def _gen_color(self):
        r, g, b = [random.randint(0, 255) for _ in range(3)]
        return "#{0:02x}{1:02x}{2:02x}".format(r, g, b)

    def register_model(self, model, fn=_grad_layers):
        layers = summarize(model, fn=fn)
        for layer_name in layers:
            self.color_for(layer_name)


def SNR(model, colors=None, fn=None, target='plot', **kwargs):
    """

    :param model:
    :param colors:
        a colors object containing layers previously indexed.
    :param fn:
        function for gathering layers
    :param target:
    :param kwargs:
        debug
    :return:
    """
    data = []
    spec = fspecs.get(target, None)
    if spec is None:
        return
    funcs = spec.get('func', None)
    lyrfn = spec.get('layer', identity) if fn is None else fn
    _sumary = summarize(model, fn=lyrfn)
    if colors is None:
        colors = LayerLegend()
    styles = _spec.get('line.dash')
    if kwargs.get('debug', None) is True:
        print(_sumary)

    for i_f, f in enumerate(funcs):
        for module_name in _sumary:
            res = {
               'layer': module_name,
               'data': spec['data'],
               'target': target,
               'func': f,
               'display': {'line': {'dash': styles[i_f],
                                    'color': colors.color_for(module_name)}}
            }
            data.append(res)
    return data, colors


def generate_layers(model, colors=None, fn=None, targets=[]):
    """

    :param model:
    :param colors:
    :param fn:
    :param targets:
    :return:
    """
    meters, plots = [], {}
    for tgt in targets:
        plots[tgt] = _def_plot.copy()
        d, colors = SNR(model, colors=colors, fn=fn, target=tgt)
        meters += d
    pprint.pprint(meters)
    pprint.pprint(plots)
    return meters, plots





# def flatten_indexed(dicts, indexes):
#     """
#
#     :param dicts:
#     :param indexes:
#     :return:
#
#     Usage:
#     indexes = ['name', 'word']
#     mydict = {'bob': {'and': {'blah':1 }, 'was': {'cat':2 }}}
#
#     flatten_indexed(mydict, indexes)
#     >> [{'name':'bob', 'word':'and', 'blah':1 },
#         {'name':'bob', 'word':'was', 'cat':2 }]
#     """
#     return


# def values(o, kys):
#     return [o.get(k) for k in kys]


# def name_type_summary(k, module):
#     if isinstance(module, nn.Linear):
#         return k
#     return None