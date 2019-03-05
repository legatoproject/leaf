"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

import json
from builtins import staticmethod
from collections import OrderedDict

from leaf.core.jsonutils import jlayer_diff, jlayer_update
from tests.testutils import LeafTestCase


class TestJsonLayers(LeafTestCase):
    @staticmethod
    def json2model(s):
        return json.loads(s, object_pairs_hook=OrderedDict)

    def test_model_update(self):
        def assert_json(left, right, diff):
            self.assertEqual(jlayer_update(TestJsonLayers.json2model(left), TestJsonLayers.json2model(diff)), TestJsonLayers.json2model(right))
            self.assertEqual(jlayer_diff(TestJsonLayers.json2model(left), TestJsonLayers.json2model(right)), TestJsonLayers.json2model(diff))
            if len(diff) == 0:
                self.assertEqual(TestJsonLayers.json2model(left), TestJsonLayers.json2model(right))

        # Check empty
        assert_json("{}", "{}", "{}")  # noqa: P103
        # Same model A & B
        assert_json(
            '{"number":1,"string":"A","object":{"list":[1,2,3],"object":{"number":42,"string":"foo","boolean":true}}}',
            '{"number":1,"string":"A","object":{"list":[1,2,3],"object":{"number":42,"string":"foo","boolean":true}}}',
            "{}",  # noqa: P103
        )
        # Update
        assert_json(
            '{"number":1,"string":"A","object":{"list":[1,2,3],"object":{"number":42,"string":"foo","boolean":true}}}',
            '{"number":1,"string":"A","object":{"list":[1,2,3],"object":{"number":1,"string":"foo","boolean":false}}}',
            '{"object":{"object":{"number":1,"boolean":false}}}',
        )
        assert_json(
            '{"number":1,"string":"A","object":{"list":[1,2,3],"object":{"number":42,"string":"foo","boolean":true}}}',
            '{"number":1,"object":{"list":[1,2,3],"object":{"number":1,"string":"foo","boolean":false}},"string2":"A"}',
            '{"string":null,"object":{"object":{"number":1,"boolean":false}},"string2":"A"}',
        )

    def test_empty_model(self):
        a = TestJsonLayers.json2model('{"a":1}')
        b = TestJsonLayers.json2model('{"a":1}')
        self.assertEqual(jlayer_diff(a, b), {})
