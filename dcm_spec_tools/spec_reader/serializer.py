import json

from dcm_spec_tools.spec_reader.condition import Condition


class DefinitionEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Condition):
            return obj.write()
        return json.JSONEncoder.default(self, obj)
