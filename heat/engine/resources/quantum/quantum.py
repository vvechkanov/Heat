# vim: tabstop=4 shiftwidth=4 softtabstop=4

#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
from quantumclient.common.exceptions import QuantumClientException

from heat.common import exception
from heat.engine import resource

from heat.openstack.common import log as logging

logger = logging.getLogger(__name__)


class QuantumResource(resource.Resource):
    def __init__(self, name, json_snippet, stack):
        super(QuantumResource, self).__init__(name, json_snippet, stack)

    def validate(self):
        '''
        Validate any of the provided params
        '''
        res = super(QuantumResource, self).validate()
        if res:
            return res
        return self.validate_properties(self.properties)

    @staticmethod
    def validate_properties(properties):
        '''
        Validates to ensure nothing in value_specs overwrites
        any key that exists in the schema.

        Also ensures that shared and tenant_id is not specified
        in value_specs.
        '''
        if 'value_specs' in properties.keys():
            vs = properties.get('value_specs')
            banned_keys = set(['shared', 'tenant_id']).union(
                properties.keys())
            for k in banned_keys.intersection(vs.keys()):
                return '%s not allowed in value_specs' % k

    @staticmethod
    def prepare_properties(properties, name):
        '''
        Prepares the property values so that they can be passed directly to
        the Quantum call.

        Removes None values and value_specs, merges value_specs with the main
        values.
        '''
        props = dict((k, v) for k, v in properties.items()
                     if v is not None and k != 'value_specs')

        if 'name' in properties.keys():
            props.setdefault('name', name)

        if 'value_specs' in properties.keys():
            props.update(properties.get('value_specs'))

        return props

    @staticmethod
    def handle_get_attributes(name, key, attributes):
        '''
        Support method for responding to FnGetAtt
        '''
        if key == 'show':
            return attributes

        if key in attributes.keys():
            return attributes[key]

        raise exception.InvalidTemplateAttribute(resource=name, key=key)

    def handle_update(self, json_snippet):
        return self.UPDATE_REPLACE

    def FnGetRefId(self):
        return unicode(self.resource_id)

    @staticmethod
    def get_secgroup_uuids(stack, props, props_name, rsrc_name, client):
        """
        Returns security group names in UUID form.

        Args:
        stack: stack associated with given resource
        props: properties described in the template
        props_name: name of security group property
        rsrc_name: name of the given resource
        client: reference to quantum client
        """
        seclist = []
        for sg in props.get(props_name):
            resource = stack.resource_by_refid(sg)
            if resource is not None:
                seclist.append(resource.resource_id)
            else:
                try:
                    client.show_security_group(sg)
                    seclist.append(sg)
                except QuantumClientException as e:
                    if e.status_code == 404:
                        raise exception.InvalidTemplateAttribute(
                            resource=rsrc_name,
                            key=props_name)
                    else:
                        raise
        return seclist
