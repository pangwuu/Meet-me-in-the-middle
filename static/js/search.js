let delay = 750;
let personCount = 2;

function addPerson() {
    const container = document.getElementById('people-container');
    const currentCount = container.querySelectorAll('.person-group').length;
    const newPersonDiv = document.createElement('div');
    newPersonDiv.className = 'person-group';
    newPersonDiv.setAttribute('data-person-index', currentCount);
    
    newPersonDiv.innerHTML = `
        <div class="person-header">
            <h3>Person ${currentCount + 1}</h3>
            <button type="button" class="remove-person" onclick="removePerson(${currentCount})">Remove</button>
        </div>
        <div class="form-row">
            <label>Name:</label>
            <input type="text" name="person_${currentCount}_name" placeholder="Enter name" required>
        </div>
        <div class="form-row">
            <label>Location:</label>
            <div class="autocomplete-container">
                <input type="text" name="person_${currentCount}_location" placeholder="Enter address or suburb" class="location-input" required>
                <div class="autocomplete-suggestions"></div>
            </div>
        </div>
        <div class="form-row">
            <label>Transport:</label>
            <select name="person_${currentCount}_transport" required>
                <option value="">Select transport method</option>
                <option value="driving">Driving</option>
                <option value="walking">Walking</option>
                <option value="bicycling">Bicycling</option>
                <option value="transit">Public Transit</option>
            </select>
        </div>
    `;
    
    container.appendChild(newPersonDiv);
    
    // Update personCount to match actual count
    personCount = container.querySelectorAll('.person-group').length;
    
    // Show remove buttons if we have more than 2 people
    updateRemoveButtons();
    
    // Setup autocomplete for the new input only
    setupAutocompleteForElement(newPersonDiv.querySelector('.location-input'));
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
    
    // Update personCount to match actual count
    personCount = personGroups.length;
}

// Setup autocomplete for a single element
function setupAutocompleteForElement(input) {
    if (!input || input.dataset.autocompleteSetup) return;
    
    // Mark as setup to avoid duplicates
    input.dataset.autocompleteSetup = 'true';
    
    let timeoutId;
    input.addEventListener('input', function() {
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
                                input.value = suggestion.description || suggestion;
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
        }, delay);
    });
    
    // Hide suggestions when clicking outside
    input.addEventListener('blur', function() {
        setTimeout(() => {
            const suggestionsDiv = this.parentNode.querySelector('.autocomplete-suggestions');
            if (suggestionsDiv) {
                suggestionsDiv.style.display = 'none';
            }
        }, 200);
    });
}

// Autocomplete functionality for all inputs
function setupAutocomplete() {
    document.querySelectorAll('.location-input').forEach(input => {
        setupAutocompleteForElement(input);
    });
}

function saveDynamicFormData() {
    const personGroups = document.querySelectorAll('.person-group');
    const peopleData = [];

    personGroups.forEach((group, index) => {
        const name = group.querySelector(`input[name="person_${index}_name"]`)?.value || '';
        const location = group.querySelector(`input[name="person_${index}_location"]`)?.value || '';
        const transport = group.querySelector(`select[name="person_${index}_transport"]`)?.value || '';
        peopleData.push({ name, location, transport });
    });

    const placeType = document.querySelector('select[name="places"]')?.value || '';
    const sortMethod = document.querySelector('select[name="sort_method"]')?.value || '';

    const searchFormData = {
        people: peopleData,
        placeType,
        sortMethod
    };

    sessionStorage.setItem('searchFormData', JSON.stringify(searchFormData));
    console.log('Saved form data:', searchFormData);
}

function addSavedData() {
    const stored = sessionStorage.getItem('searchFormData');
    if (!stored) return;

    const { people, placeType, sortMethod } = JSON.parse(stored);

    // Fill in people
    const container = document.getElementById('people-container');

    // Clear any initial people
    container.innerHTML = '';

    people.forEach((person, index) => {
        const personGroup = document.createElement('div');
        personGroup.classList.add('person-group');
        personGroup.dataset.personIndex = index;

        personGroup.innerHTML = `
            <div class="person-header">
                <h3>Person ${index + 1}</h3>
                <button type="button" class="remove-person" onclick="removePerson(${index})">Remove</button>
            </div>
            <div class="form-row">
                <label>Name:</label>
                <input type="text" name="person_${index}_name" value="${person.name || ''}" required>
            </div>
            <div class="form-row">
                <label>Location:</label>
                <div class="autocomplete-container">
                    <input type="text" name="person_${index}_location" value="${person.location || ''}" class="location-input" required>
                    <div class="autocomplete-suggestions"></div>
                </div>
            </div>
            <div class="form-row">
                <label>Transport:</label>
                <select name="person_${index}_transport" required>
                    <option value="">Select transport method</option>
                    <option value="driving" ${person.transport === 'driving' ? 'selected' : ''}>Driving</option>
                    <option value="walking" ${person.transport === 'walking' ? 'selected' : ''}>Walking</option>
                    <option value="bicycling" ${person.transport === 'bicycling' ? 'selected' : ''}>Bicycling</option>
                    <option value="transit" ${person.transport === 'transit' ? 'selected' : ''}>Public Transit</option>
                </select>
            </div>
        `;
        container.appendChild(personGroup);
    });

    // Update personCount to match restored data
    personCount = people.length;

    // Fill in place type and sort method
    if (placeType) {
        const placeSelect = document.querySelector('select[name="places"]');
        if (placeSelect) placeSelect.value = placeType;
    }
    if (sortMethod) {
        const sortSelect = document.querySelector('select[name="sort_method"]');
        if (sortSelect) sortSelect.value = sortMethod;
    }

    console.log('Restored form data:', { people, placeType, sortMethod });
}

// Initialize autocomplete for existing inputs
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('searchForm');
    if (form) {
        form.addEventListener('submit', saveDynamicFormData);
    }

    addSavedData();
    setupAutocomplete();
    updateRemoveButtons();
});