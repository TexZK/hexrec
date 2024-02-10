{{ name | escape | underline }}

.. currentmodule:: {{ module }}

.. autoclass:: {{ objname }}
    :members:
    :inherited-members:
    :private-members:
    :special-members:


{% block attributes %}
{% if attributes %}
    .. rubric:: {{ _('Attributes') }}

    .. autosummary::
{% for item in attributes %}
        ~{{ name }}.{{ item }}
{%- endfor %}
{% endif %}
{% endblock %}


{% block methods %}
{% if methods %}
    .. rubric:: {{ _('Methods') }}

    .. autosummary::
        :nosignatures:
{% for item in methods %}
        ~{{ name }}.{{ item }}
{%- endfor %}
{% endif %}
{% endblock %}
