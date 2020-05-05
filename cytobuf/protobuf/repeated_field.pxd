cdef extern from "google/protobuf/repeated_field.h" namespace "google::protobuf":
    cdef cppclass RepeatedField[Element]:
        RepeatedField()
        RepeatedField& operator=(const RepeatedField&)
        bint empty() const
        int size() const
        const Element& Get(int) const
        Element* Mutable(int)
        Element& operator[](int index)
        Element& at(int index)
        void Set(int index, const Element& value)
        void Add(const Element& value)

    cdef cppclass RepeatedPtrField[Element]:
        RepeatedPtrField()
        RepeatedPtrField& operator=(const RepeatedPtrField&)
        bint empty() const
        int size() const
        const Element& Get(int) const
        Element* Mutable(int)
        Element& operator[](int index)
        Element& at(int index)
        void Set(int index, const Element& value)
        void Add(const Element& value)