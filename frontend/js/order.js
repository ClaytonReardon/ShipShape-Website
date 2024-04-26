document.addEventListener('DOMContentLoaded', function() {
  updateStock('Rations', 'stock_rations');
  updateStock('laser_crystals', 'stock_laser_crystals');
  updateStock('droid_silicon', 'stock_droid_silicon');
  updateStock('capacitors', 'stock_capacitors');
  updateStock('fuel', 'stock_fuel');
});

const localFunctionUrl  = 'http://localhost:7071/api/Order'

function updateStock(itemName, elementId) {
  fetch(`${localFunctionUrl}?item=${encodeURIComponent(itemName)}`)
      .then(response => response.json())
      .then(data => {
          document.getElementById(elementId).innerText = `In stock: ${data}`;
      })
      .catch(error => {
          console.error('Failed to fetch stock data:', error);
          document.getElementById(elementId).innerText = 'In stock: Unavailable';
      });
}

function orderItem(itemName, quantity) {
  const data = { item: itemName, quantity: quantity };

  fetch(localFunctionUrl, {
    method: 'POST',
    body: JSON.stringify(data),
    headers: {
      'Content-Type': 'application/json'
    }
  })

  .then(response => {
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.text();
  })
  .then(data => {
    console.log(data);
    let elementId = 'stock_' + itemName.toLowerCase().replace(' ', '_'); // Assuming the itemName format needs adjusting
    updateStock(itemName.toLowerCase(), elementId);
  })
  .catch(error => {
    console.log(`Failed to order ${quantity} of ${itemName}: ${error}`);
  });
}