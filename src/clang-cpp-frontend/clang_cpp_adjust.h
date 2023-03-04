#ifndef CLANG_CPP_FRONTEND_CLANG_CPP_ADJUST_H_
#define CLANG_CPP_FRONTEND_CLANG_CPP_ADJUST_H_

#include <clang-c-frontend/clang_c_adjust.h>

/**
 * clang C++ adjuster class for:
 *  - symbol adjustment, dealing with ESBMC-IR `symbolt`
 *  - expression adjustment, dealing with ESBMC-IR `exprt` or other IRs derived from exprt
 *  - code adjustment, dealing with ESBMC-IR `codet` or other IRs derived from codet
 *  - implicit code generation, e.g. generate implicit GOTO code for vptr initializations in ctors
 *
 * Some ancillary methods to support the expr/code adjustments above
 */
class clang_cpp_adjust : public clang_c_adjust
{
public:
  explicit clang_cpp_adjust(contextt &_context);
  virtual ~clang_cpp_adjust() = default;

  /**
   * methods for symbol adjustment
   */
  void adjust_symbol(symbolt &symbol);

  /**
   * methods for code (codet) adjustment
   * and other IRs derived from codet
   */
  void adjust_while(codet &code) override;
  void adjust_switch(codet &code) override;
  void adjust_for(codet &code) override;
  void adjust_ifthenelse(codet &code) override;
  void adjust_decl_block(codet &code) override;

  /**
   * methods for expression (exprt) adjustment
   * and other IRs derived from exprt
   */
  void adjust_member(member_exprt &expr) override;
  void adjust_side_effect(side_effect_exprt &expr) override;
  void adjust_new(exprt &expr);
  void adjust_struct_method_call(member_exprt &expr);

  /**
   * methods for implicit GOTO code generation
   */
  void gen_vptr_initializations(symbolt &symbol);
  /*
   * generate vptr initialization code for constructor:
   *  this->VptrBLAH@BLAH = $vtable::BLAH
   *
   * Params:
   *  - comp: vptr component as in class' type `components` vector
   *  - ctor_type: type of the constructor symbol
   *  - new_code: the code expression for vptr initialization
   */
  void gen_vptr_init_code(
    const struct_union_typet::componentt &comp,
    side_effect_exprt &new_code,
    const code_typet &ctor_type);
  void gen_vptr_init_lhs(
    const struct_union_typet::componentt &comp,
    exprt& lhs_code,
    const code_typet &ctor_type);
  void gen_vptr_init_rhs(
    const struct_union_typet::componentt &comp,
    exprt& rhs_code,
    const code_typet &ctor_type);

  /**
   * ancillary methods to support the expr/code adjustments above
   */
  void convert_expression_to_code(exprt &expr);
};

#endif /* CLANG_CPP_FRONTEND_CLANG_CPP_ADJUST_H_ */
