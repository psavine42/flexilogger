from pytorchart.utils import deep_merge, deepcopy


_plot_defs = {
    'simple':
        {'plots': {'value': {'type': 'line'}},
         'meters':  {'value': {'type': 'AverageValueMeter', 'target': 'value'}}},
     # todo other stuff # class accuracy, AUC, PUCT ImageMeter
     'image':
         {'plots': {'image': {'type': 'image'}},
          'meters': {'image': {'type': 'ImageMeter', 'target': 'image'}}},
     'confusion':
         {'plots': {'confusion_view': {'type': 'image'}},
          'meters': {'confusion': {'type': 'ConfusionMeter', 'target': 'confusion_view'}}},
     'acc':
         {'plots': {'acc': {'type': 'line'}},
          'meters': {'acc': {'type': 'AverageValueMeter', 'target': 'acc'}}},
     'mse':
         {'plots': {'mse': {'type': 'line'}},
          'meters': {'mse': {'type': 'MSEMeter', 'target': 'mse'}}},
     'loss':
         {'plots': {'loss': {'type': 'line'}},
          'meters': {'loss': {'type': 'AverageValueMeter', 'target': 'loss'}}}
}

_default_phases = ['train', 'test']


class Config(object):
    """
    Static object for generating meter and plot configurations

    """
    @classmethod
    def _build_phases(cls, k, phases, target=None, c=None):
        "given a meter key, create copies for each phase and add target"
        meter_cfg = {}
        mk = k if c is None else c
        plt = _plot_defs.get(k, {})
        spec = deepcopy(plt)
        for k, v in spec.get('meters', {}).items():
            for phase in phases:
                meter = deepcopy(v)
                if target is not None:
                    meter['target'] = target
                meter['phase'] = phase
                meter_cfg[phase + '_' + mk] = meter
        spec['meters'] = meter_cfg
        return spec

    @classmethod
    def gen_plot(cls, *keys, phases=None, plot=None):
        """
        Creates a plot from the specified keys.

        :param keys: list of strings
        :param phases: list of strings or None. If None, it will use default
        phases of ['test', ['train']
        :param plot: name of plot

        :return: tuple of dicts for plots and meters
        """
        if phases is None:
            phases = _default_phases
        cfg = deep_merge(*[cls._build_phases('simple', phases, target=plot, c=k) for k in keys])
        if plot is not None:
            plt = deepcopy(cfg['plots']['value'])
            cfg['plots'][plot] = plt
        return cfg['plots'], cfg['meters']

    @classmethod
    def get_presets(cls, *keys, phases=None):
        """
        generate a dictionary of plots and meters given preconfigured keys.
        This will create a meter by key by phase.

        :param keys: list of strings
        :param phases: list of strings or None. If None, it will use default
        phases of ['test', ['train']

        :return: tuple of dicts for plots and meters

        """
        if phases is None:
            phases = _default_phases
        cfg = deep_merge(*[cls._build_phases(k, phases) for k in keys])
        return cfg['plots'], cfg['meters']

    @classmethod
    def default_cfg(cls):
        """
        return a the base configuration for plot and meter
        :return: dict

        :Usage:

        Config.default_cfg()
        """
        return _plot_defs.get('simple', {})


def get_meters(*keys, phases=_default_phases):
    _, meters = Config.get_presets(*keys, phases=phases)
    for k, meter in meters.items():
        meter.pop('target', None)
    return meters


# METERS AND PLOT INFO
def preset_names():
    """
    Get a list of configured plots

    :return: list of strings
    """
    return list(_plot_defs.keys())


# def plot_types():
#     return _meters
#
#
# def meter_types():
#     return _meters


# def meter_info(name):
#     return meter_defs.get(name, None)


# PRESET CONFIGURATIONS
# def get_preset_logger(key, **kwargs):
#     if key in _plot_defs:
#         cfg = _plot_defs[key]
#         return FlexLogger(cfg['plots'], cfg['meters'], **kwargs)


#
# def get_preset(key):
#     cfg = _plot_defs.get(key, None)
#     return cfg['plots'], cfg['meters']


# def get_presets(*keys, phases=_default_phases):
#     return Config.get_presets(*keys, phases=phases)



