# PYTHONPATH needs to include the path to $Z3DIR/python.
# And on debian jessie for some reason I need to LD_PRELOAD librt.so?

# Future work: facilities for using the ESBMC flatteners to handle subsets of
# SMT. These are available to C++, but currently too sketchy for python right
# now.

# XXX -- it would appear that smt_sort's aren't auto-downcasted to the correct
# wrapped sort kind, _even_ if it's passed through downcast_sort?

import esbmc
import z3

class Z3sort(esbmc.solve.smt_sort):
    def __init__(self, z3sort, kind, width=None, domain_width=None):
        if domain_width != None:
            super(Z3sort, self).__init__(kind, width, domain_width)
        elif width != None:
            super(Z3sort, self).__init__(kind, width)
        else:
            super(Z3sort, self).__init__(kind)
        self.sort = z3sort

  # Has no other methods, only provides id / data_width / dom_width in base
  # class, so that the rest of smt_convt can decide the right path.

class Z3ast(esbmc.solve.smt_ast):
    def __init__(self, ast, convobj, sort):
        super(Z3ast, self).__init__(convobj, sort)
        self.ast = ast
        self.conv = convobj
        self.z3sort = sort # self.sort loses type info? Needs investigation

    def ite(self, conv, cond, falseop):
        assert False

    def eq(self, conv, other):
        new_ast_ref = self.ast == other.ast
        new_ast = Z3ast(new_ast_ref, self.conv, self.conv.bool_sort)
        # Also manually stash this ast
        self.conv.ast_list.append(new_ast)
        return new_ast

    def update(self, conv, value, idx, idx_expr):
        # Either a tuple update or an array update. Alas, all the exprs baked
        # into ESBMC make no distinguishment.
        if self.sort.id == esbmc.solve.smt_sort_kind.array:
            domain_sort = self.z3sort.dom_sort
            int_val = esbmc.BigInt(idx)
            idx = conv.mk_smt_bvint(int_val, False, domain_sort.data_width)
            res = z3.Update(self.ast, idx.ast, value.ast)
            result = Z3ast(res, self.conv, self.sort)
        else:
            assert self.sort.id == esbmc.solve.smt_sort_kind.struct
            # Hurrrr. Project all fields out except this one; update; create
            # new tuple.
            decls = self.z3sort.proj_decls

            # Place the tuple ast in an ast array
            inp_array = (z3.Ast * 1)()
            inp_array[0] = self.ast.ast

            # Now apply projection functions to the tuple ast. Need to apply
            # ExprRef immediately, or z3 will immediately gc it.
            projected = [z3.ExprRef(z3.Z3_mk_app(conv.ctx.ctx, x.ast, 1, inp_array), conv.ctx) for x in decls]

            # Zip with their sorts
            asts_and_sorts = zip(projected, self.z3sort.sub_sorts)
            # Put Z3ast around the outside
            projected = [Z3ast(ar, conv, sort) for ar, sort in asts_and_sorts]

            # We now have a list of all current tuple values. We need to update
            # the identified one with the designated value
            projected[idx] = value

            result = conv._tuple_create(projected, self.z3sort)

        # Also manually stash this ast
        self.conv.ast_list.append(result)
        return result

    def select(self, conv, idx):
        if self.sort.id == esbmc.solve.smt_sort_kind.array:
            idx = conv.convert_ast(idx)
            ast = z3.Select(self.ast, idx.ast)
            result = Z3ast(ast, self.conv, self.sort)
        else:
            assert False # XXX is only arrays anyway?
        # Also manually stash this ast
        self.conv.ast_list.append(result)
        return result

    def project(self, conv, elem):
        assert self.sort.id == esbmc.solve.smt_sort_kind.struct
        proj_decl = self.z3sort.proj_decls[elem]

        # We need to manually apply this function to project the elem out
        inp_array = (z3.Ast * 1)()
        inp_array[0] = self.ast.ast
        projected_ast = z3.Z3_mk_app(conv.ctx.ctx, proj_decl.ast, 1, inp_array)

        result = Z3ast(projected_ast, self.conv, self.z3sort.sub_sorts[elem])
        # Also manually stash this ast
        self.conv.ast_list.append(result)
        return result

class Z3python(esbmc.solve.smt_convt):
    def __init__(self, ns):
        super(Z3python, self).__init__(False, ns, False, True, True)
        self.ctx = z3.Context()
        self.ast_list = []
        self.sort_list = []
        self.bool_sort = self.mk_sort((esbmc.solve.smt_sort_kind.bool,))
        self.solver = z3.Solver(solver=None, ctx=self.ctx)

        self.func_map = {
            esbmc.solve.smt_func_kind.ite :
                lambda ctx, args, asts: z3.If(asts[0], asts[1], asts[2], ctx),
            esbmc.solve.smt_func_kind.eq :
                lambda ctx, args, asts: asts[0] == asts[1],
            esbmc.solve.smt_func_kind.noteq :
                lambda ctx, args, asts: asts[0] != asts[1],
            esbmc.solve.smt_func_kind._or : # or is a keyword in python
                lambda ctx, args, asts: z3.Or(asts[0], asts[1]),
            esbmc.solve.smt_func_kind._not :
                lambda ctx, args, asts: z3.Not(asts[0]),
            esbmc.solve.smt_func_kind.implies :
                lambda ctx, args, asts: z3.Implies(asts[0], asts[1], ctx),
            esbmc.solve.smt_func_kind.bvadd :
                lambda ctx, args, asts: asts[0] + asts[1],
            esbmc.solve.smt_func_kind.bvugt :
                lambda ctx, args, asts: z3.UGT(asts[0], asts[1]),
            esbmc.solve.smt_func_kind.bvult :
                lambda ctx, args, asts: z3.ULT(asts[0], asts[1]),
            esbmc.solve.smt_func_kind.concat :
                lambda ctx, args, asts: z3.Concat(asts[0], asts[1]),
            esbmc.solve.smt_func_kind.bvlshr :
                lambda ctx, args, asts: z3.LShR(asts[0], asts[1]),
            esbmc.solve.smt_func_kind.bvashr :
                lambda ctx, args, asts: asts[0] >> asts[1],
        }

        # Various accounting structures for the address space modeling need to
        # be set up, but that needs to happen after the solver is online. Thus,
        # we have to call this once the object is ready to create asts.
        self.smt_post_init()

    # Decorator function: return a function that appends the return value to
    # the list of asts. This is vital: the python object returned from various
    # functions needs to live as long as the convt object, so we need to keep
    # a reference to it
    def stash_ast(func):
        def tmp(self, *args, **kwargs):
            ast = func(self, *args, **kwargs)
            self.ast_list.append(ast)
            return ast
        return tmp

    def stash_sort(func):
        def tmp(self, *args, **kwargs):
            sort = func(self, *args, **kwargs)
            self.sort_list.append(sort)
            return sort
        return tmp

    @stash_ast
    def mk_func_app(self, sort, k, args):
        asts = [x.ast for x in args]
        if k in self.func_map:
            z3ast = self.func_map[k](self.ctx, args, asts)
            return Z3ast(z3ast, self, sort)
        print "Unimplemented SMT function {}".format(k)
        assert False

    def assert_ast(self, ast):
        self.solver.add(ast.ast)

    def dec_solve(self):
        #self.solver.check()
        res = self.solver.check()
        if res == z3.sat:
            return esbmc.solve.smt_result.sat
        elif res == z3.unsat:
            return esbmc.solve.smt_result.unsat
        else:
            return esbmc.solve.smt_result.error

    def solve_text(self):
        return "Z3 solver, from python"

    @stash_sort
    def mk_sort(self, args):
        kind = args[0]
        if kind == esbmc.solve.smt_sort_kind.bool:
            return Z3sort(z3.BoolSort(self.ctx), kind)
        elif kind == esbmc.solve.smt_sort_kind.bv:
            width = args[1]
            z3sort = z3.BitVecSort(width, self.ctx)
            return Z3sort(z3sort, kind, args[1])
        elif kind == esbmc.solve.smt_sort_kind.array:
            domain = args[1]
            range_ = args[2]
            arr_sort = z3.ArraySort(domain.sort, range_.sort)
            range_width = range_.data_width if range_.data_width != 0 else 1
            assert domain.data_width != 0
            res_sort = Z3sort(arr_sort, kind, range_width, domain.data_width)
            res_sort.dom_sort = domain
            res_sort.range_sort = range_
            return res_sort
        else:
            print kind
            assert False

    @stash_sort
    def mk_struct_sort(self, t):
        # Due to the sins of the fathers, struct arrays get passed through this
        # api too. Essentially, it's ``anything that contains a struct''.
        if t.type_id == esbmc.type.type_ids.struct:
            return self.mk_struct_sort2(t)
        else:
            subtype = esbmc.downcast_type(t.subtype)
            struct_sort = self.mk_struct_sort2(subtype)
            dom_width = self.calculate_array_domain_width(t)
            width_sort = z3.BitVecSort(dom_width, self.ctx)
            arr_sort = z3.ArraySort(width_sort, struct_sort.sort)
            result = Z3sort(arr_sort, esbmc.solve.smt_sort_kind.array, 1, dom_width)
            result.dom_sort = Z3sort(width_sort, esbmc.solve.smt_sort_kind.bv, dom_width)
            result.range_sort = struct_sort
            return result

    def mk_struct_sort2(self, t):
        # Z3 tuples don't _appear_ to be exported to python. Therefore we have
        # to funnel some pointers into it manually, via ctypes.
        num_fields = len(t.member_names)

        # Create names for fields. The multiplication syntax is ctypes way to
        # allocate an array.
        ast_vec = (z3.Symbol * num_fields)()
        i = 0
        for x in t.member_names:
            ast_vec[i] = z3.Symbol(x.as_string())
            i += 1

        # Create types. These are Z3sorts, that contain a z3.SortRef, which
        # in turn contains a z3.Sort. The latter is what we need to funnel
        # into ctype function call.
        sort_vec = (z3.Sort * num_fields)()
        sub_sorts = [self.convert_sort(x) for x in t.members]
        i = 0
        for i in range(len(sub_sorts)):
            sort_vec[i] = sub_sorts[i].sort.ast

        # Name for this type
        z3_sym = z3.Symbol(t.typename.as_string())

        # Allocate output ptrs -- function for creating the object, and for
        # projecting fields.
        ret_decl = (z3.FuncDecl * 1)()
        proj_decl = (z3.FuncDecl * num_fields)()
        sort_ref = z3.Z3_mk_tuple_sort(self.ctx.ctx, z3_sym, num_fields, ast_vec, sort_vec, ret_decl, proj_decl)

        # Reference management: output operands start with zero references IIRC,
        # We want to keep a handle on the returned sort_ref, and the FuncDecl
        # typed ast, for creation of new tuples. The projection decls need to
        # be kept so that we can extract fields from the tuple.
        finsort = Z3sort(z3.BoolSortRef(sort_ref, self.ctx), esbmc.solve.smt_sort_kind.struct)
        proj_decls = [z3.FuncDeclRef(x) for x in proj_decl]
        finsort.decl_ref = z3.FuncDeclRef(ret_decl[0])
        finsort.proj_decls = proj_decls
        finsort.sub_sorts = sub_sorts
        return finsort

    @stash_ast
    def tuple_create(self, expr):
        # This is another facility we have to implement with z3's ctypes
        # interface.
        # First convert all expr fields to being z3 asts
        asts = [self.convert_ast(x) for x in expr.members]

        # Create the corresponding type
        tsort = self.convert_sort(expr.type)

        return self._tuple_create(asts, tsort)

    def _tuple_create(self, asts, sort):
        ast_array = (z3.Ast * len(asts))()
        for x in range(len(asts)):
            ast_array[x] = asts[x].ast.ast

        tast = z3.Z3_mk_app(self.ctx.ctx, sort.decl_ref.ast, len(asts), ast_array)
        tref = z3.ExprRef(tast, self.ctx)
        return Z3ast(tref, self, sort)

    def mk_smt_int(self, theint, sign):
        assert False

    @stash_ast
    def mk_smt_bool(self, value):
        return Z3ast(z3.BoolVal(value, self.ctx), self, self.bool_sort)

    @stash_ast
    def mk_smt_symbol(self, name, sort):
        z3var = z3.Const(name, sort.sort)
        return Z3ast(z3var, self, sort)

    @stash_ast
    def mk_tuple_symbol(self, name, sort):
        # In z3, tuple symbols are the same as normal symbols
        z3var = z3.Const(name, sort.sort)
        return Z3ast(z3var, self, sort)

    @stash_ast
    def mk_array_symbol(self, name, sort, subtype):
        # Same for arrays
        z3var = z3.Const(name, sort.sort)
        return Z3ast(z3var, self, sort)

    @stash_ast
    def mk_tuple_array_symbol(self, expr):
        # Same for tuple arrays
        assert type(expr) == esbmc.expr.symbol
        sort = self.convert_sort(expr.type)
        z3var = z3.Const(expr.name.as_string(), sort.sort)
        return Z3ast(z3var, self, sort)

    def mk_smt_real(self, str):
        assert False

    @stash_ast
    def mk_smt_bvint(self, theint, sign, w):
        bvsort = self.mk_sort([esbmc.solve.smt_sort_kind.bv, w])
        z3ast = z3.BitVecVal(theint.to_long(), w, self.ctx)
        return Z3ast(z3ast, self, bvsort)

    @stash_ast
    def convert_array_of(self, val, domain_width):
        # Z3 directly supports initialized constant arrays
        dom = z3.BitVecSort(domain_width, self.ctx)
        ast = z3.K(dom, val.ast)

        result_sort_ast = ast.sort()
        z3_result_sort = Z3sort(result_sort_ast, esbmc.solve.smt_sort_kind.array, val.sort.data_width, domain_width)

        return Z3ast(ast, self, z3_result_sort)

    # XXX -- the get methods are called during counterexample building, and
    # require the creation of a esbmc expr representing the given ast. This
    # is fairly self explanatory and so implementing it isn't going to be that
    # illustrative, you just have to be familiar with the esbmc expr structure
    # and your own AST type.
    def get_bool(self, ast):
        assert False

    def get_bv(self, thetype, ast):
        assert False

    def l_get(self, ast):
        assert False

    @stash_ast
    def mk_extract(self, a, high, low, s):
        ast = z3.Extract(high, low, a.ast)
        return Z3ast(ast, self, s)
