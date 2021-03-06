# The piwheels project
#   Copyright (c) 2017 Ben Nuttall <https://github.com/bennuttall>
#   Copyright (c) 2017 Dave Jones <dave@waveform.org.uk>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"A simple HTML tag builder based loosely on Genshi's concepts"

# Most of the classes and functions below have slightly odd names as they're
# aping built-in types like str and/or meant to be used as one would use a
# function (again, like str).
# pylint: disable=invalid-name


class literal(str):
    "A str sub-class that assumes its content is HTML"
    def __html__(self):
        return self


class content(str):
    "A str sub-class which escapes content for inclusion in HTML"
    def __html__(self):
        return literal(self.
                       replace('&', '&amp;').
                       replace('"', '&quot;').
                       replace('<', '&lt;').
                       replace('>', '&gt;'))


def html(s):
    "Return s in a form suitable for inclusion in an HTML document"
    try:
        return s.__html__()
    except AttributeError:
        return content(s).__html__()


# The set of HTML elements which should never have a closing tag

EMPTY_ELEMENTS = (
    # From HTML4 standard
    'area',
    'base',
    'basefont',
    'br',
    'col',
    'frame',
    'hr',
    'img',
    'input',
    'isindex',
    'link',
    'meta',
    'param',
    # Proprietary extensions
    'bgsound',
    'embed',
    'keygen',
    'spacer',
    'wbr',
)


class TagFactory:
    """
    A factory class for generating XML/HTML elements (or tags).

    Instances of this class use __getattr__ magic to provide methods for
    generating any XML or HTML element. Calling a method with a particular name
    will return a string containing an XML/HTML element of that name. Any
    positional arguments will be used as content for the element, and any named
    arguments will be used as attributes for the element. If the element or
    attribute you wish to name is a reserved word in Python, you can simply
    append underscore ("_") to the name (all trailing underscore characters
    will be stripped implicitly).

    For example::

        >>> tag = TagFactory()
        >>> tag.a()
        '<a></a>'
        >>> tag.a('foo')
        '<a>foo</a>'
        >>> tag.a('foo', bar='baz')
        '<a bar="baz">foo</a>'

    You can explicitly suppress the generation of either the opening or
    closing tags by setting the ``_open`` and ``_close`` parameters to False
    respectively::

        >>> tag = TagFactory()
        >>> tag.a(_close=False)
        '<a>'
        >>> tag.form(_open=False)
        '</form>'

    Note that content of a tag is only output when ``_open`` is True (or
    omitted). The factory will automatically set ``_close`` to True for HTML
    tags which are declared "empty" in the standard, e.g. ``<br>`` and
    ``<hr>``::

        >>> tag = TagFactory()
        >>> tag.br()
        '<br>'

    If the factory is instantiated with the xml parameter set to True, this
    automatic behaviour will be disabled so that all empty tags are explicitly
    closed::

        >>> tag = TagFactory(xml=True)
        >>> tag.hr()
        '<hr/>'
    """
    # The public methods of this class are generated on the fly by __getattr__
    # pylint: disable=too-few-public-methods

    def __init__(self, xml=False):
        self._xml = xml

    def _format(self, obj):
        if isinstance(obj, str):
            return html(obj)
        elif isinstance(obj, bytes):
            return html(obj.decode('utf-8'))
        else:
            try:
                return literal(''.join(self._format(item) for item in obj))
            except TypeError:
                return html(obj)

    def _generate(self, _tag, *args, **kwargs):
        _tag = _tag.rstrip('_')
        result = ''
        open_tag = kwargs.get('_open', True)
        close_tag = kwargs.get('_close', _tag.lower() not in EMPTY_ELEMENTS)
        empty_tag = not args
        if open_tag:
            if empty_tag and not close_tag and self._xml:
                template = '<%s%s/>'
            else:
                template = '<%s%s>'
            result += template % (
                _tag,
                ''.join(
                    ' %s="%s"' % (
                        attr_name, self._format(attr_name if attr_val is True
                                                else attr_val)
                    )
                    for (_name, attr_val) in kwargs.items()
                    for attr_name in (_name.rstrip('_').replace('_', '-'),)
                    if attr_val is not None and attr_val is not False)
            )
            for arg in args:
                result += self._format(arg)
        if close_tag:
            result += '</%s>' % _tag
        return literal(result)

    def __getattr__(self, attr):
        def generator(*args, **kwargs):
            # pylint: disable=missing-docstring
            return self._generate(attr, *args, **kwargs)
        setattr(self, attr, generator)
        return generator


tag = TagFactory()
