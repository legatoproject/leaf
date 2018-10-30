'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''

import json
import unittest
from builtins import staticmethod
from collections import OrderedDict

from leaf.model.modelutils import layerModelDiff, layerModelUpdate


class TestJsonLayers(unittest.TestCase):

    @staticmethod
    def json2model(s):
        return json.loads(s, object_pairs_hook=OrderedDict)

    def testModelUpdate(self):

        def assertJson(left, right, diff):
            self.assertEqual(
                layerModelUpdate(
                    TestJsonLayers.json2model(left),
                    TestJsonLayers.json2model(diff)),
                TestJsonLayers.json2model(right))
            self.assertEqual(
                layerModelDiff(
                    TestJsonLayers.json2model(left),
                    TestJsonLayers.json2model(right)),
                TestJsonLayers.json2model(diff))
            if len(diff) == 0:
                self.assertEqual(
                    TestJsonLayers.json2model(left),
                    TestJsonLayers.json2model(right))

        # Check empty
        assertJson(
            '{}',
            '{}',
            '{}')
        # Same model A & B
        assertJson(
            '{"number":1,"string":"A","object":{"list":[1,2,3],"object":{"number":42,"string":"foo","boolean":true}}}',
            '{"number":1,"string":"A","object":{"list":[1,2,3],"object":{"number":42,"string":"foo","boolean":true}}}',
            '{}')
        # Update
        assertJson(
            '{"number":1,"string":"A","object":{"list":[1,2,3],"object":{"number":42,"string":"foo","boolean":true}}}',
            '{"number":1,"string":"A","object":{"list":[1,2,3],"object":{"number":1,"string":"foo","boolean":false}}}',
            '{"object":{"object":{"number":1,"boolean":false}}}')
        assertJson(
            '{"number":1,"string":"A","object":{"list":[1,2,3],"object":{"number":42,"string":"foo","boolean":true}}}',
            '{"number":1,"object":{"list":[1,2,3],"object":{"number":1,"string":"foo","boolean":false}},"string2":"A"}',
            '{"string":null,"object":{"object":{"number":1,"boolean":false}},"string2":"A"}')

    def testEmptyModel(self):
        a = TestJsonLayers.json2model('{"a":1}')
        b = TestJsonLayers.json2model('{"a":1}')
        self.assertEqual(layerModelDiff(a, b), {})
