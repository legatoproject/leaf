from argparse import ArgumentParser

from leaf.core.utils import Version

OPERATOR_LABELS = {
    Version.__gt__: ("-gt", ">"),
    Version.__ge__: ("-ge", ">="),
    Version.__lt__: ("-lt", "<"),
    Version.__le__: ("-le", "<="),
    Version.__eq__: ("-eq", "=="),
    Version.__ne__: ("-ne", "!="),
}


def leaf_version_compare():
    parser = ArgumentParser(description="Leaf version comparator")
    group = parser.add_mutually_exclusive_group()
    group.required = True
    for op, tup in OPERATOR_LABELS.items():
        group.add_argument(tup[0], dest="operator", action="store_const", const=op, help="Compare A {0} B".format(tup[1]))
    parser.add_argument("a", metavar="A", nargs=1, type=Version, help="version A")
    parser.add_argument("b", metavar="B", nargs=1, type=Version, help="version B")

    args = parser.parse_args()
    a, b, op = args.a[0], args.b[0], args.operator
    out = op(a, b)
    print("{out}: {a} {op} {b}".format(a=a, b=b, op=OPERATOR_LABELS[op][1], out=out))
    return 0 if out else 1
