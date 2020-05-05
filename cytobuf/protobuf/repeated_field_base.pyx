cdef class RepeatedFieldBase:
    def __cinit__(self):
        pass

    def __iter__(self):
        cdef int i
        for i in range(self._instance.size()):
            yield self._instance.at(i)

    def __len__(self):
        return self._instance.size()

    def __getitem__(self, key):
        cdef int size, index, start, stop, step
        size = self._instance.size()
        if isinstance(key, int):
            index = key
            if index < 0:
                index = size + index
            if not 0 <= index < size:
                raise IndexError(f"list index ({key}) out of range")
            return self._instance.at(index)
        else:
            start, stop, step = key.indices(size)
            return [
                (self._instance.at(index))
                for index in range(start, stop, step)
            ]

    def add(self, PyType value):
        self._instance.Add(value)