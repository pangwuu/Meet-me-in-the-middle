
let personCount = 2;

function addPerson() {
    const container = document.getElementById('people-container');
    const newPersonDiv = document.createElement('div');
    newPersonDiv.className = 'person-group';
    newPersonDiv.setAttribute('data-person-index', personCount);
    
    newPersonDiv.innerHTML = `
        <div class="person-header">
            <h3>Person ${personCount + 1}</h3>
            <button type="button" class="remove-person" onclick="removePerson(${personCount})">Remove</button>
        </div>
        <div class="form-row">
            <label>Name:</label>
            <input type="text" name="person_${personCount}_name" placeholder="Enter name" required>
        </div>
        <div class="form-row">
            <label>Location:</label>
            <div class="autocomplete-container">
                <input type="text" name="person_${personCount}_location" placeholder="Enter address or suburb" class="location-input" required>
                <div class="autocomplete-suggestions"></div>
            </div>
        </div>
        <div class="form-row">
            <label>Transport:</label>
            <select name="person_${personCount}_transport" required>
                <option value="">Select transport method</option>
                <option value="driving">Driving</option>
                <option value="walking">Walking</option>
                <option value="bicycling">Bicycling</option>
                <option value="transit">Public Transit</option>
            </select>
        </div>
    `;
    
    container.appendChild(newPersonDiv);
    personCount++;
    
    // Show remove buttons if we have more than 2 people
    updateRemoveButtons();
    
    // Setup autocomplete for the new input
    setupAutocomplete();
}

function removePerson(index) {
    const personDiv = document.querySelector(`[data-person-index="${index}"]`);
    if (personDiv) {
        personDiv.remove();
        updateRemoveButtons();
        renumberPeople();
    }
}

function updateRemoveButtons() {
    const personGroups = document.querySelectorAll('.person-group');
    const removeButtons = document.querySelectorAll('.remove-person');
    
    removeButtons.forEach((button, index) => {
        if (personGroups.length > 2) {
            button.style.display = 'inline-block';
        } else {
            button.style.display = 'none';
        }
    });
}

function renumberPeople() {
    const personGroups = document.querySelectorAll('.person-group');
    personGroups.forEach((group, index) => {
        group.setAttribute('data-person-index', index);
        group.querySelector('h3').textContent = `Person ${index + 1}`;
        
        // Update form field names
        const nameInput = group.querySelector('input[name*="_name"]');
        const locationInput = group.querySelector('input[name*="_location"]');
        const transportSelect = group.querySelector('select[name*="_transport"]');
        const removeButton = group.querySelector('.remove-person');
        
        if (nameInput) nameInput.name = `person_${index}_name`;
        if (locationInput) locationInput.name = `person_${index}_location`;
        if (transportSelect) transportSelect.name = `person_${index}_transport`;
        if (removeButton) removeButton.setAttribute('onclick', `removePerson(${index})`);
    });
    
    personCount = personGroups.length;
}

// Autocomplete functionality
function setupAutocomplete() {
    document.querySelectorAll('.location-input').forEach(input => {
        // Remove existing event listeners to avoid duplicates
        const newInput = input.cloneNode(true);
        input.parentNode.replaceChild(newInput, input);
        
        let timeoutId;
        newInput.addEventListener('input', function() {
            clearTimeout(timeoutId);
            const query = this.value;
            const suggestionsDiv = this.parentNode.querySelector('.autocomplete-suggestions');
            
            if (query.length < 3) {
                suggestionsDiv.style.display = 'none';
                return;
            }
            
            timeoutId = setTimeout(() => {
                fetch(`/api/autocomplete?q=${encodeURIComponent(query)}`)
                    .then(response => response.json())
                    .then(data => {
                        suggestionsDiv.innerHTML = '';
                        if (data.length > 0) {
                            data.forEach(suggestion => {
                                const div = document.createElement('div');
                                div.className = 'autocomplete-suggestion';
                                div.textContent = suggestion.description || suggestion;
                                div.addEventListener('click', () => {
                                    newInput.value = suggestion.description || suggestion;
                                    suggestionsDiv.style.display = 'none';
                                });
                                suggestionsDiv.appendChild(div);
                            });
                            suggestionsDiv.style.display = 'block';
                        } else {
                            suggestionsDiv.style.display = 'none';
                        }
                    })
                    .catch(error => {
                        console.error('Autocomplete error:', error);
                        suggestionsDiv.style.display = 'none';
                    });
            }, 750);
        });
        
        // Hide suggestions when clicking outside
        newInput.addEventListener('blur', function() {
            setTimeout(() => {
                this.parentNode.querySelector('.autocomplete-suggestions').style.display = 'none';
            }, 200);
        });
    });
}

// Initialize autocomplete for existing inputs
document.addEventListener('DOMContentLoaded', function() {
    setupAutocomplete();
    updateRemoveButtons();
});