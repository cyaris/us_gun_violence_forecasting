// returning the array without the remove_item
function removeItemFromArray(array, remove_item) {
  return array.filter(function (array_item) {
    return array_item !== remove_item
  })
}

function getTextWidth(svgInput, textInput, fontSize) {
  // obtaining length of any textinput (based on default font size and font family)
  textWidthArray = []

  svgInput
    .append("g")
    .selectAll(".dummyText")
    .data([textInput])
    .enter()
    .append("text")
    .attr("pointer-events", "none")
    // .attr('font-family', 'sans-serif')
    .attr("font-size", fontSize)
    .text(function (d) {
      return d
    })
    .each(function (d, i) {
      thisWidth = this.getComputedTextLength()
      textWidthArray.push(thisWidth)
      this.remove()
    })

  return textWidthArray.reduce((a, b) => a + b, 0)
}

// returning the max value from any array
function maxFromArray(array) {
  return array.reduce(function (a, b) {
    return Math.max(a, b)
  })
}

// returning the min value from any array
function minFromArray(array) {
  return array.reduce(function (a, b) {
    return Math.min(a, b)
  })
}

// returning average overall value across all numbers in an array.
function arrayAverage(array) {
  // Find the sum
  sumOfAllItems = 0

  for (i in array) {
    sumOfAllItems += array[i]
  }
  // get the length of the array
  itemCount = array.length

  // return the average
  return sumOfAllItems / itemCount
}

// unique values from array part
// returning all non null values from an array with no duplicates
// null values will be counted as zero (only once).
Array.prototype.coalesceZeroUnique = function () {
  array = []

  for (var i = 0; i < this.length; i++) {
    // not adding any values to the array that have already been added
    if (array.includes(this[i])) {
    } else if (this[i] == null && array.includes(0)) {
    } else if (isNaN(this[i]) && array.includes(0)) {
    }
    // adding zeros instead of null values to the array
    else if (this[i] == null) {
      array.push(0)
    } else if (isNaN(this[i])) {
      array.push(0)
    } else {
      array.push(this[i])
    }
  }

  return array.sort()
}

Array.prototype.nonNull = function () {
  array = []
  for (var i = 0; i < this.length; i++) {
    if (this[i] == null) {
    } else if (isNaN(this[i])) {
    } else {
      array.push(this[i])
    }
  }
  return array
}
