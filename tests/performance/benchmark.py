import argparse
import gc
import json
import linecache
import random
import string
import sys
from itertools import chain
from timeit import Timer

from google.protobuf import json_format
from google.protobuf.internal import api_implementation
from memory_profiler import LineProfiler

from cytobuf_pb.addressbook.models.addressbook_pb2 import AddressBook as CyAddressBook

sys.path.append('../../scratch/py')

from pb.addressbook.models.addressbook_pb2 import AddressBook as CppAddressBook
from pb.people.models.people_pb2 import Person as CppPerson
from pyrobuf_flat_pb import AddressBook as PyroAddressBook

NS_PER_SEC = 1e9


def random_string(length=8):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))


def run_timeit(function, title, baseline=None):
    timer = Timer(function)
    iterations, _ = timer.autorange()
    raw_timings = timer.repeat(3, iterations)
    per_iteration_timings_ns = [dt / iterations for dt in raw_timings]
    best_ns = min(per_iteration_timings_ns)
    result = best_ns * NS_PER_SEC
    speedup_str = ''
    if baseline:
        speedup_str = f' {baseline/result:,.2f} X Speedup'
    print(f'{title}\t{result:,.2f}ns{speedup_str}')
    return result


def _measure_memory_inner(constructor, serialized_string, iterations):
    values = []
    # baseline
    for _ in range(iterations):
        value = constructor()
        value.ParseFromString(serialized_string)
        values.append(value)
    # allocated
    values.clear()
    del values
    del value
    # cleared
    gc.collect()
    # collected
    return None


def measure_memory(*args, **kwargs):
    gc.collect()
    result = {}
    profiler = LineProfiler(backend='psutil')
    func = profiler(_measure_memory_inner)
    func(*args, **kwargs)
    for (filename, lines) in profiler.code_map.items():
        all_lines = linecache.getlines(filename)
        last_mem = None
        for (lineno, mem) in lines:
            if mem is None:
                result[all_lines[lineno - 1].strip()[2:]] = last_mem[1]
            last_mem = mem
    return result


def benchmark_memory(name, baseline_proto, proto_class, baseline_allocated_memory=None):
    memory_result = measure_memory(proto_class, baseline_proto, 5000)
    allocated_memory = memory_result['allocated'] - memory_result['baseline']
    comparision_str = ''
    if baseline_allocated_memory is not None:
        percentage_drop = ((baseline_allocated_memory - allocated_memory) / baseline_allocated_memory) * 100
        drop_label = 'Decrease'
        if percentage_drop < 0:
            percentage_drop = abs(percentage_drop)
            drop_label = 'Increase'
        comparision_str = f'  ({percentage_drop:,.2f}% {drop_label})'
    print(f'\t{name} Memory for 5k protos:\t{allocated_memory:,.2f}MB{comparision_str}')
    return allocated_memory


def build_baseline_proto(item_count):
    baseline = CppAddressBook()
    for _ in range(item_count):
        new_person = baseline.people.add()
        new_person.name = f'{random_string(4)} {random_string(5)}'
        new_person.email = f'{random_string(6)}@email.com'
        new_person.id = 1234
        for _ in range(3):
            new_phone = new_person.phones.add()
            new_phone.number = f'+1425{random.randint(1000000, 9999999)}'
            new_phone.type = CppPerson.PhoneType.MOBILE
    baseline_proto = baseline.SerializeToString()
    return baseline_proto


def main():
    parser = argparse.ArgumentParser(
        description='Runs a benchmark of Marshmallow.')
    parser.add_argument('--items', type=str, default='1,10,100',
                        help='Comma-seperated list of number of items in the protobuf')
    args = parser.parse_args()
    items = [int(x.strip()) for x in args.items.split(',')]
    if api_implementation.Type() != 'cpp':
        print("*** WARNING google.protobuf isn't using the native extension ***")

    print('***** Benchmark Results *****')
    for item_count in items:
        print(f'\n{item_count} Items per proto:')
        baseline_proto = build_baseline_proto(item_count)

        cython_address_book = CyAddressBook()
        cpp_address_book = CppAddressBook()
        pyro_address_book = PyroAddressBook()
        cpp_address_book.ParseFromString(baseline_proto)
        cython_address_book.ParseFromString(baseline_proto)
        pyro_address_book.ParseFromString(baseline_proto)
        json_str = json_format.MessageToJson(cpp_address_book).encode('utf-8')
        py_dict = json.loads(json_str)
        cpp_person = cpp_address_book.people[0]
        cython_person = cython_address_book.people[0]
        pyrobuf_person = pyro_address_book.people[0]
        python_person = py_dict['people'][0]
        print('\t*** Compute ***')
        benchmarks = {
            'Parse': {
                'json.loads': lambda: json.loads(json_str),
                'baseline': lambda: cpp_address_book.ParseFromString(baseline_proto),
                'cytobuf': lambda: cython_address_book.ParseFromString(baseline_proto),
                'pyrobuf': lambda: pyro_address_book.ParseFromString(baseline_proto),
            },
            'Serialize': {
                'json.dumps': lambda: json.loads(json_str),
                'baseline': lambda: cpp_address_book.SerializeToString(),
                'cytobuf': lambda: cython_address_book.SerializeToString(),
                'pyrobuf': lambda: pyro_address_book.SerializeToString(),
            },
            'FromJson': {
                'baseline': lambda: json_format.Parse(json_str, cpp_address_book),
                'cytobuf': lambda: cython_address_book.FromJsonString(json_str),
                'pyrobuf': lambda: pyro_address_book.ParseFromJson(json_str),
            },
            'ToJson': {
                'baseline': lambda: json_format.MessageToJson(cpp_address_book),
                'cytobuf': lambda: cython_address_book.ToJsonString(),
                'pyrobuf': lambda: pyro_address_book.SerializeToJson(),
            },
            'Iterate': {
                'json': lambda: list(py_dict['people']),
                'baseline': lambda: list(cpp_address_book.people),
                'cytobuf': lambda: list(cython_address_book.people),
                'pyrobuf': lambda: list(pyro_address_book.people)
            },
            'Field Access': {
                'json': lambda: python_person['name'],
                'baseline': lambda: cpp_person.name,
                'cytobuf': lambda: cython_person.name,
                'pyrobuf': lambda: pyrobuf_person.name
            }
        }
        longest_implementation = len(
            max(
                chain.from_iterable([[keys for keys in variant.keys()] for variant in benchmarks.values()]),
                key=len
            )
        )
        for title, variants in benchmarks.items():
            print(f"\t{title}:")
            baseline = None
            for implementation, function in variants.items():
                result = run_timeit(function, f'\t\t{implementation.ljust(longest_implementation)}', baseline)
                if implementation == 'baseline':
                    baseline = result

        print('\n\t*** Memory ***')
        baseline = benchmark_memory('baseline', baseline_proto, CppAddressBook)
        benchmark_memory('cytobuf ', baseline_proto, CyAddressBook, baseline)
        benchmark_memory('pyrobuf ', baseline_proto, PyroAddressBook, baseline)


if __name__ == "__main__":
    main()
