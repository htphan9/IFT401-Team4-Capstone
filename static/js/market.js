// market.js — handles the Buy/Sell trade modal on the market page
// Run once the page has fully loaded
document.addEventListener('DOMContentLoaded', function () {

    // Keep track of the current modal state so we can recalculate on the fly
    var modalState = {
        action: '',
        price: 0,
        owned: 0,
        avgCost: 0,
        balance: 0
    };

    // Grab references to modal elements
    var quantityInput = document.getElementById('modal-quantity');
    var confirmInput = document.getElementById('modal-confirm');
    var submitBtn = document.getElementById('modal-submit-btn');
    var warningEl = document.getElementById('modal-warning');
    var totalCostEl = document.getElementById('modal-total-cost');
    var remainingEl = document.getElementById('modal-remaining');
    var ownedEl = document.getElementById('modal-owned');
    var pnlEl = document.getElementById('modal-pnl');
    var pnlRow = document.getElementById('modal-pnl-row');
    var confirmWord = document.getElementById('modal-confirm-word');
    var maxBtn = document.getElementById('modal-max-btn');

    // Recalculate the trade summary every time quantity changes
    function updateModalStats() {
        var quantity = parseInt(quantityInput.value) || 0;
        var price = modalState.price;
        var totalCost = quantity * price;
        var hasWarning = false;

        // Update total cost display
        totalCostEl.textContent = '$' + totalCost.toFixed(2);

        // Calculate estimated remaining balance
        var remaining = 0;
        if (modalState.action === 'buy') {
            remaining = modalState.balance - totalCost;
        } else {
            remaining = modalState.balance + totalCost;
        }
        remainingEl.textContent = '$' + remaining.toFixed(2);

        // Color the remaining balance red if it goes negative
        if (remaining < 0) {
            remainingEl.className = 'text-danger';
        } else {
            remainingEl.className = '';
        }

        // Show P&L only when selling
        if (modalState.action === 'sell') {
            pnlRow.classList.remove('d-none');
            var pnlValue = (price - modalState.avgCost) * quantity;
            if (pnlValue >= 0) {
                pnlEl.textContent = '+$' + pnlValue.toFixed(2);
                pnlEl.className = 'text-success';
            } else {
                pnlEl.textContent = '-$' + Math.abs(pnlValue).toFixed(2);
                pnlEl.className = 'text-danger';
            }
        } else {
            pnlRow.classList.add('d-none');
        }

        // Warning checks
        warningEl.classList.add('d-none');
        warningEl.textContent = '';

        if (modalState.action === 'buy' && totalCost > modalState.balance) {
            warningEl.textContent = 'Insufficient Funds';
            warningEl.classList.remove('d-none');
            hasWarning = true;
        }
        if (modalState.action === 'sell' && quantity > modalState.owned) {
            warningEl.textContent = 'Insufficient Shares Owned';
            warningEl.classList.remove('d-none');
            hasWarning = true;
        }

        // Check confirmation input and warnings to decide if submit is allowed
        checkSubmitState(hasWarning);
    }

    // Enable or disable the submit button based on warnings and confirmation text
    function checkSubmitState(hasWarning) {
        var typed = confirmInput.value.trim().toLowerCase();
        if (!hasWarning && typed === modalState.action) {
            submitBtn.disabled = false;
        } else {
            submitBtn.disabled = true;
        }
    }


    // Attach a click listener to every Buy and Sell button
    document.querySelectorAll('.trade-btn').forEach(function (button) {
        button.addEventListener('click', function () {

            // Read the stock info stored in the button's data attributes
            var action  = this.dataset.action;
            var stockId = this.dataset.stockId;
            var ticker  = this.dataset.ticker;
            var price   = parseFloat(this.dataset.price);
            var owned   = parseInt(this.dataset.owned) || 0;
            var avgCost = parseFloat(this.dataset.avgCost) || 0;

            // Read user balance from the page
            var balanceEl = document.getElementById('user-balance');
            var balance = parseFloat(balanceEl.dataset.balance) || 0;

            // Save state
            modalState.action = action;
            modalState.price = price;
            modalState.owned = owned;
            modalState.avgCost = avgCost;
            modalState.balance = balance;

            // Update the modal title to "Buy AAPL" or "Sell AAPL"
            document.getElementById('tradeModalLabel').textContent =
                (action === 'buy' ? 'Buy ' : 'Sell ') + ticker;

            // Pass the stock id and action into the hidden form fields
            document.getElementById('modal-stock-id').value = stockId;
            document.getElementById('modal-action').value   = action;

            // Show the current price inside the modal
            document.getElementById('modal-price-display').textContent =
                'Current Price: $' + price.toFixed(2) + ' per share';

            // Show shares owned
            ownedEl.textContent = owned.toLocaleString();

            // Update the confirmation word label
            confirmWord.textContent = action;

            // Style the submit button
            submitBtn.textContent = action === 'buy' ? 'Confirm Buy' : 'Confirm Sell';
            submitBtn.className   = action === 'buy'
                ? 'btn btn-green-sm w-100'
                : 'btn btn-red-sm w-100';

            // Reset the form fields
            quantityInput.value = 1;
            confirmInput.value = '';
            submitBtn.disabled = true;

            // Calculate initial stats
            updateModalStats();
        });
    });

    // Recalculate when user changes the quantity
    quantityInput.addEventListener('input', function () {
        updateModalStats();
    });

    // Check the confirmation text as user types
    confirmInput.addEventListener('input', function () {
        updateModalStats();
    });

    // Max button — fill in the max quantity the user can buy or sell
    maxBtn.addEventListener('click', function () {
        if (modalState.action === 'buy') {
            var maxShares = Math.floor(modalState.balance / modalState.price);
            if (maxShares < 1) maxShares = 1;
            quantityInput.value = maxShares;
        } else {
            quantityInput.value = modalState.owned > 0 ? modalState.owned : 1;
        }
        updateModalStats();
    });

    // Poll the server for updated stock prices every 1 minute
    function fetchPrices() {
        fetch('/api/prices')
            .then(function (response) {
                return response.json();
            })
            .then(function (data) {
                // Loop through each stock in the response
                for (var stockId in data) {
                    var stock = data[stockId];
                    var priceStr = '$' + stock.price.toFixed(2);

                    // Update price cell (works on both market and portfolio pages)
                    var priceCell = document.getElementById('price-' + stockId);
                    if (priceCell) {
                        priceCell.textContent = priceStr;
                    }

                    // Update daily high cell (market page)
                    var highCell = document.getElementById('high-' + stockId);
                    if (highCell) {
                        highCell.textContent = stock.high ? '$' + stock.high.toFixed(2) : '-';
                    }

                    // Update daily low cell (market page)
                    var lowCell = document.getElementById('low-' + stockId);
                    if (lowCell) {
                        lowCell.textContent = stock.low ? '$' + stock.low.toFixed(2) : '-';
                    }

                    // Update available shares cell (market page)
                    var availCell = document.getElementById('available-' + stockId);
                    if (availCell) {
                        availCell.textContent = stock.available.toLocaleString();
                    }

                    // Update data-price on Buy/Sell buttons so the modal shows the latest price
                    var buyBtn = document.getElementById('buy-btn-' + stockId);
                    if (buyBtn) {
                        buyBtn.dataset.available = stock.available;
                    }
                    var sellBtn = document.getElementById('sell-btn-' + stockId);
                    if (sellBtn) {
                        sellBtn.dataset.price = stock.price;
                    }

                    // Recalculate total value and unrealized P&L (portfolio page)
                    var valueCell = document.getElementById('value-' + stockId);
                    var pnlCell = document.getElementById('pnl-' + stockId);
                    if (valueCell && pnlCell) {
                        var row = pnlCell.closest('tr');
                        var shares = parseFloat(row.dataset.shares);
                        var avgCost = parseFloat(row.dataset.avgCost);

                        var totalValue = stock.price * shares;
                        var totalCost = avgCost * shares;
                        var pnl = totalValue - totalCost;

                        valueCell.textContent = '$' + totalValue.toFixed(2);

                        // Update P&L text and color
                        if (pnl >= 0) {
                            pnlCell.textContent = '+$' + pnl.toFixed(2);
                            pnlCell.className = 'text-success';
                        } else {
                            pnlCell.textContent = '-$' + Math.abs(pnl).toFixed(2);
                            pnlCell.className = 'text-danger';
                        }
                    }
                }
            });
    }

    // Fetch prices right away on page load, then every 1 minute
    fetchPrices();
    setInterval(fetchPrices, 60000); //60000 for 1 minute

});