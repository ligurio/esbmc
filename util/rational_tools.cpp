/*******************************************************************\

Module: Rational Numbers

Author: Daniel Kroening, kroening@kroening.com

\*******************************************************************/

#include "rational_tools.h"

/*******************************************************************\

Function: power10

  Inputs:

 Outputs:

 Purpose:

\*******************************************************************/

static mp_integer power10(unsigned i)
{
  mp_integer result=1;

  for(; i!=0; i--)
    result*=10;

  return result;
}

/*******************************************************************\

Function: to_rational

  Inputs:

 Outputs:

 Purpose:

\*******************************************************************/

bool to_rational(const exprt &expr, rationalt &rational_value)
{
  if(expr.id()!="constant") return true;

  const std::string &value=expr.value().as_string();

  std::string no1, no2;
  char mode=0;

  for(unsigned i=0; i<value.size(); i++)
  {
    char ch=value[i];

    if(isdigit(ch))
    {
      if(mode==0)
        no1+=ch;
      else
        no2+=ch;
    }
    else if(ch=='/' || ch=='.')
    {
      if(mode==0)
        mode=ch;
      else
        return true;
    }
    else
      return true;
  }

  switch(mode)
  {
   case 0:
    rational_value=string2integer(no1);
    break;

   case '.':
    rational_value=string2integer(no1);
    rational_value+=rationalt(string2integer(no2))/power10(no2.size());
    break;

   case '/':
    rational_value=string2integer(no1);
    rational_value/=string2integer(no2);
    break;

   default:
    return true;
  }    

  return false;
}

/*******************************************************************\

Function: from_rational

  Inputs:

 Outputs:

 Purpose:

\*******************************************************************/

bool from_rational(const rationalt &rational_value, exprt &expr)
{
  return true;
}
