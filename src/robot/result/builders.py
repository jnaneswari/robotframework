#  Copyright 2008-2011 Nokia Siemens Networks Oyj
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from robot.result.model import ExecutionResult, Message, CombinedExecutionResult
from robot.utils.etreewrapper import ET


def ResultsFromXML(*sources):
    if len(sources) == 1:
        return ExecutionResultBuilder(sources[0]).build(ExecutionResult())
    return CombinedExecutionResult(*[ResultsFromXML(src) for src in sources])


class ExecutionResultBuilder(object):

    def __init__(self, source):
        self._source = source

    def build(self, result):
        elements = ElementStack(RootElement(result))
        for action, elem in ET.iterparse(self._source, events=('start', 'end')):
            getattr(elements, action)(elem)
        return result


class ElementStack(object):

    def __init__(self, root_element):
        self._elements = [root_element]

    @property
    def _current(self):
        return self._elements[-1]

    def start(self, elem):
        self._elements.append(self._current.child_element(elem.tag))
        self._current.start(elem)

    def end(self, elem):
        self._current.end(elem)
        elem.clear()
        self._elements.pop()


class _Element(object):
    tag = ''

    def __init__(self, result):
        self._result = result

    def start(self, elem):
        pass

    def end(self, elem):
        pass

    def child_element(self, tag):
        for child_type in self._children():
            if child_type.tag == tag:
                return child_type(self._result)
        return IgnoredElement(result=None)

    def _children(self):
        return []


class RootElement(_Element):

    def _children(self):
        return [RobotElement]


class RobotElement(_Element):
    tag = 'robot'

    def _children(self):
        return [RootSuiteElement, ErrorsElement]


class SuiteElement(_Element):
    tag = 'suite'

    def start(self, elem):
        self._result = self._result.suites.create(name=elem.get('name'),
                                                  source=elem.get('source'))

    def _children(self):
        return [SuiteElement, DocElement, StatusElement,
                KeywordElement, TestCaseElement, MetadataElement]


class RootSuiteElement(SuiteElement):

    def start(self, elem):
        self._result = self._result.suite
        self._result.name = elem.get('name')
        self._result.source = elem.get('source')


class TestCaseElement(_Element):
    tag = 'test'

    def start(self, elem):
        self._result = self._result.tests.create(name=elem.get('name'))

    def _children(self):
        return [KeywordElement, TagsElement, DocElement, TestStatusElement]


class KeywordElement(_Element):
    tag = 'kw'

    def start(self, elem):
        self._result = self._result.keywords.create(name=elem.get('name'),
                                                    timeout=elem.get('timeout'),
                                                    type=elem.get('type'))

    def _children(self):
        return [DocElement, ArgumentsElement, KeywordElement, MessageElement,
                StatusElement]


class MessageElement(_Element):
    tag = 'msg'

    def start(self, elem):
        self._result = self._result.messages.create(
            level=elem.get('level'),
            timestamp=elem.get('timestamp'),
            html=elem.get('html', False),
            linkable=elem.get('linkable', False))

    def end(self, elem):
        self._result.message = elem.text or ''


class StatusElement(_Element):
    tag = 'status'

    def start(self, elem):
        self._result.status = elem.get('status')
        self._result.starttime = elem.get('starttime')
        self._result.endtime = elem.get('endtime')


class TestStatusElement(StatusElement):

    def start(self, elem):
        StatusElement.start(self, elem)
        self._result.critical = elem.get('critical')


class DocElement(_Element):
    tag = 'doc'

    def end(self, elem):
        self._result.doc = elem.text or ''


class MetadataElement(_Element):
    tag = 'metadata'

    def _children(self):
        return [MetadataItemElement]


class MetadataItemElement(_Element):
    tag = 'item'

    def _children(self):
        return [MetadataItemElement]

    def end(self, elem):
        self._result.metadata[elem.get('name')] = elem.text


class TagsElement(_Element):
    tag = 'tags'

    def _children(self):
        return [TagElement]


class TagElement(_Element):
    tag = 'tag'

    def end(self, elem):
        self._result.tags.add(elem.text)


class ArgumentsElement(_Element):
    tag = 'arguments'

    def _children(self):
        return [ArgumentElement]


class ArgumentElement(_Element):
    tag = 'arg'

    def end(self, elem):
        self._result.args.append(elem.text)


class ErrorsElement(_Element):
    tag = 'errors'

    def start(self, elem):
        self._result = self._result.errors

    def _children(self):
        return [MessageElement]


class IgnoredElement(_Element):
    pass
