SrecTag
=======

.. currentmodule:: hexrec.formats.srec

.. autoclass:: SrecTag
    :members:
    :inherited-members:
    :private-members:
    :special-members:




    .. rubric:: Attributes

    .. autosummary::

        ~SrecTag.real
        ~SrecTag.imag
        ~SrecTag.numerator
        ~SrecTag.denominator
        ~SrecTag.HEADER
        ~SrecTag.DATA_16
        ~SrecTag.DATA_24
        ~SrecTag.DATA_32
        ~SrecTag.RESERVED
        ~SrecTag.COUNT_16
        ~SrecTag.COUNT_24
        ~SrecTag.START_32
        ~SrecTag.START_24
        ~SrecTag.START_16






    .. rubric:: Methods

    .. autosummary::
        :nosignatures:

        ~SrecTag.is_data
        ~SrecTag.is_file_termination
        ~SrecTag.conjugate
        ~SrecTag.bit_length
        ~SrecTag.bit_count
        ~SrecTag.to_bytes
        ~SrecTag.from_bytes
        ~SrecTag.as_integer_ratio
        ~SrecTag.is_integer
        ~SrecTag.fit_count_tag
        ~SrecTag.fit_data_tag
        ~SrecTag.fit_start_tag
        ~SrecTag.get_address_max
        ~SrecTag.get_address_size
        ~SrecTag.get_data_max
        ~SrecTag.get_tag_match
        ~SrecTag.is_count
        ~SrecTag.is_header
        ~SrecTag.is_start
        ~SrecTag.__init__

