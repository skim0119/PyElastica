//==============================================================================
/*!
//  \file
//  \brief Utilities for zero and zero length vectors
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
#include "Utilities/Math/Accuracy.hpp"
#include "Utilities/Math/SqrLength.hpp"
#include "Utilities/Math/Vec3.hpp"

namespace elastica {

  //****************************************************************************
  /*!\brief Checks for a zero number
   */
  inline auto is_zero(real_t real_number) noexcept -> bool {
    return ::blaze::isZero(real_number);
  }
  //****************************************************************************

  //****************************************************************************
  /*!\brief Checks for a zero vector
   */
  inline auto is_zero(const Vec3& vec) noexcept -> bool {
    return ::blaze::isZero(vec);
  }
  //****************************************************************************

  //****************************************************************************
  /*!\brief Checks for a zero length vector
   *
   * Checks if the length of a vector is zero or as close to zero that it
   * can not be distinguished form zero
   */
  inline auto is_zero_length(const Vec3& vec) noexcept -> bool {
    //          return vec.sqrLength() < Limits<real_t>::fpuAccuracy();
    return sqrLength(vec) < accuracy;
  }
  //****************************************************************************

  //****************************************************************************
  /*!\brief Returns a zero vector
   */
  inline auto zero3() noexcept -> Vec3 {
    return Vec3{static_cast<real_t>(0.0), static_cast<real_t>(0.0),
                static_cast<real_t>(0.0)};
  }
  //****************************************************************************

}  // namespace elastica
