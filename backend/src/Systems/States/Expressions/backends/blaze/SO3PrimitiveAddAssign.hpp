/*!
//  \file
//  \brief Definition of SO3_primitive_add_assign for interfacing blaze types
//  with \elastica states
//
//  Copyright (C) 2020-2020 Tejaswin Parthasarathy - All Rights Reserved
//  Copyright (C) 2020-2020 MattiaLab - All Rights Reserved
//
//  Distributed under the MIT License.
//  See LICENSE.txt for details.
*/
//==============================================================================

#pragma once

//******************************************************************************
// Includes
//******************************************************************************
#include <blaze_tensor/math/DynamicTensor.h>
//
#include "Systems/States/Expressions/backends/Declarations.hpp"
#include "Systems/States/Expressions/backends/blaze/SO3PrimitiveAddAssign/BaseTemplate.hpp"
#include "Systems/States/Expressions/backends/blaze/SO3PrimitiveAddAssign/SIMD.hpp"
#include "Systems/States/Expressions/backends/blaze/SO3PrimitiveAddAssign/Scalar.hpp"
#include "Systems/States/Expressions/backends/blaze/SO3PrimitiveAssign.hpp"
#include "Systems/States/Expressions/backends/blaze/Size.hpp"

namespace elastica {

  namespace states {

    template <typename T, typename RHSVectorBatch>
    auto SO3_primitive_add_assign(blaze::DynamicTensor<T>& lhs_matrix_batch,
                                  RHSVectorBatch const& rhs_vector) noexcept
        -> void {
      /*
       * This version creates memory every time
      auto temp_to_synch(lhs_matrix_batch);  // TODO: avoid making new memory
                                             // (but not sure how)
      // The rotation computation cannot be computed asynchronously during
      // add_assign.
      SO3_primitive_assign(lhs_matrix_batch, temp_to_synch, rhs_vector);
      */

      detail::SO3AddAssign<detail::backend_choice<detail::SO3AddAssignKind>()>::
          apply(lhs_matrix_batch, rhs_vector);
    }

  }  // namespace states

}  // namespace elastica
