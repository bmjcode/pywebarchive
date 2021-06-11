"""Utility classes and functions for internal use."""

from base64 import b64encode
from html import escape
from html.parser import HTMLParser
from urllib.parse import urljoin


__all__ = ["MainResourceProcessor", "base64_string", "bytes_to_str"]


class MainResourceProcessor(HTMLParser):
    """Class to process the main resource in the webarchive.

    This class uses HTMLParser to rewrite the main resource's HTML code
    to make changes necessary to render the extracted page:

      * All href and src attributes referring to subresources in the
        archive are changed to point to the local extracted copies.

      * The optional srcset attribute is removed from <img> tags, since
        it causes rendering problems when extracting webarchives saved by
        older versions of Safari that don't support that attribute.
    """

    __slots__ = ["_url", "_root", "_subresources", "_local_paths", "_output"]

    def __init__(self, url, root, subresources, local_paths, output):
        """Return a new MainResourceProcessor."""

        HTMLParser.__init__(self, convert_charrefs=False)

        self._url = url
        self._root = root
        self._subresources = subresources
        self._local_paths = local_paths
        self._output = output

    def handle_starttag(self, tag, attrs):
        """Handle the start of a tag."""

        if self._root is None:
            inline_content = None

            if tag == "link":
                link_href = None
                is_stylesheet = False
                for attr, value in attrs:
                    if attr == "rel" and value.lower() == "stylesheet":
                        is_stylesheet = True
                    elif attr == "href":
                        link_href = self._absolute_url(value)
                if is_stylesheet:
                    # Replace this link with an inline <style> block
                    content = ""
                    for subresource in self._subresources:
                        if subresource.url == link_href:
                            content = escape(bytes_to_str(subresource.data))
                            break
                    # Bypass the standard logic since we're replacing this
                    # with an entirely different tag
                    self._output.write("<style>{0}</style>".format(content))
                    return

            elif tag == "script":
                for i, (attr, value) in enumerate(attrs):
                    if attr == "src":
                        # Include the script content inline
                        script_src = self._absolute_url(value)
                        for subresource in self._subresources:
                            if subresource.url == script_src:
                                # HTML entities in <script> are NOT escaped
                                inline_content = bytes_to_str(subresource.data)
                                break
                        # Remove the src attribute
                        del attrs[i]

        # Open the tag
        tag_data = ["<", tag]

        # Process attributes
        for attr, value in attrs:
            if self._root is None:
                # Embed external resources inline with HTML
                if tag == "link" and attr == "href":
                    link_href = self._absolute_url(value)

            elif tag == "img" and attr == "srcset":
                # Omit the srcset attribute, which is not supported by older
                # versions of Safari (including the obsolete 5.1.7 for Windows,
                # which is the only version I have available to test with).
                continue

            tag_data.append(" ")
            tag_data.append(attr)
            tag_data.append('="')
            tag_data.append(self._process_attr_value(tag, attr, value))
            tag_data.append('"')

        # Close the tag
        tag_data.append(">")

        # If this is the opening <html> tag, indicate that this file
        # has been processed
        if tag == "html":
            tag_data.insert(0, "<!-- Processed by pywebarchive -->\n")

        self._output.write("".join(tag_data))
        if self._root is None and inline_content:
            self._output.write(inline_content)

    def handle_endtag(self, tag):
        """Handle the end of a tag."""

        self._output.write("</{0}>".format(tag))

    def handle_data(self, data):
        """Handle arbitrary data."""

        self._output.write(escape(data, False))

    def handle_entityref(self, name):
        """Handle a named character reference."""

        self._output.write("&{0};".format(name))

    def handle_charref(self, name):
        """Handle a numeric character reference."""

        self._output.write("&#{0};".format(name))

    def handle_comment(self, data):
        """Handle a comment."""

        # Note IE conditional comments potentially can affect rendering
        self._output.write("<!--{0}-->".format(data))

    def handle_decl(self, decl):
        """Handle a doctype declaration."""

        # This should probably be on its own line
        self._output.write("<!{0}>\n".format(decl))

    def _absolute_url(self, url):
        """Return the absolute URL to the specified resource."""

        return urljoin(self._url, url)

    def _resource_url(self, orig_url):
        """Return an appropriate URL for the specified resource.

        If the resource exists in this archive, this will be its local path.
        Otherwise, it will be the absolute URL to the original resource.
        """

        # Get the absolute URL of the original resource
        abs_url = self._absolute_url(orig_url)

        if abs_url in self._local_paths:
            # Return the local path to this resource
            if self._root:
                return "{0}/{1}".format(self._root,
                                        self._local_paths[abs_url])
            else:
                return self._local_paths[abs_url]

        else:
            # Return the absolute URL to this resource
            return abs_url

    def _process_attr_value(self, tag, attr, value):
        """Process the value of a tag's attribute."""

        if tag == "a" and attr == "href":
            # Always rewrite href's for <a> tags relative to the original URL
            value = urljoin(self._url, value)

        elif tag == "img":
            if attr == "src" and self._root is None:
                # Embed this image using a data URL
                for subresource in self._subresources:
                    if subresource.url == self._absolute_url(value):
                        value = "data:{0};base64,{1}".format(
                            subresource.mime_type,
                            base64_string(subresource.data)
                        )

            if attr == "srcset":
                # Process the HTML5 srcset attribute
                srcset = []
                for item in map(str.strip, value.split(",")):
                    src, res = item.split(" ", 1)
                    src = self._resource_url(src)
                    srcset.append("{0} {1}".format(src, res))
            
                value = ", ".join(srcset)

        elif attr in ("action", "href", "src"):
            value = self._resource_url(value)

        return escape(value, True)


def base64_string(data, altchars=None):
    """Return data encoded as a base64 string."""
    return bytes_to_str(b64encode(data, altchars))


def bytes_to_str(data):
    """Convert bytes to str."""
    return "".join(map(chr, data))
