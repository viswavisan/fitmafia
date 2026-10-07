// Global variable to store current member data for editing
let currentMemberData = null;
let cameraStream = null;
const { currentUserRole, currentUserName, currentMember } = globalThis.APP_CONFIG;

// --- Helper function for cache busting ---
function addCacheBuster(url) {
    if (!url) return '';
    const timestamp = Date.now();
    // Check if URL already has query parameters
    if (url.includes('?')) {
        return `${url}&_=${timestamp}`;
    } else {
        return `${url}?_=${timestamp}`;
    }
}

// Status options for showFlashMessage: 'success', 'danger', 'warning', 'info', 'primary', 'secondary'
function showFlashMessage(message, status = 'danger') {
    const flashesContainer = document.querySelector('.flashes');
    if (!flashesContainer) return;

    const alert = document.createElement('div');
    alert.className = `alert alert-${status} alert-dismissible fade show`;
    alert.setAttribute('role', 'alert');
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    flashesContainer.appendChild(alert);

    setTimeout(() => {
        const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
        if (bsAlert) {
            bsAlert.close();
        }
    }, 5000);
}

function autoCloseFlashes() {
    const alerts = document.querySelectorAll('.flashes .alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 5000);
    });
}



const openCameraBtn = document.getElementById('openCameraBtn');
if (openCameraBtn) {
    openCameraBtn.addEventListener('click', async () => {
        const overlay = document.getElementById('cameraOverlay');
        const video = document.getElementById('cameraVideo');

        try {
            cameraStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } });
            video.srcObject = cameraStream;
            overlay.classList.remove('d-none');
        } catch (err) {
            console.error("Error accessing camera:", err);
            showFlashMessage("Could not access camera. Please ensure permissions are granted.", "warning");
        }
    });
}

const closeCameraBtn = document.getElementById('closeCameraBtn');
if (closeCameraBtn) {
    closeCameraBtn.addEventListener('click', () => {
        closeCamera();
    });
}

const captureBtn = document.getElementById('captureBtn');
if (captureBtn) {
    captureBtn.addEventListener('click', () => {
        const video = document.getElementById('cameraVideo');
        const canvas = document.getElementById('cameraCanvas');

        // Match canvas dimensions to video
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        // Draw video frame to canvas
        const context = canvas.getContext('2d');
        context.drawImage(video, 0, 0, canvas.width, canvas.height);

        // Get image data as base64
        const imageData = canvas.toDataURL('image/jpeg');

        // Store in hidden input and show preview
        document.getElementById('capturedPhotoData').value = imageData;
        const preview = document.getElementById('photoPreview');
        preview.src = imageData;
        preview.style.display = 'block';

        // Clear file input if a photo is captured
        document.getElementById('photo').value = '';

        closeCamera();
    });
}

// Also preview if a file is chosen via the normal file input
const photoInput = document.getElementById('photo');
if (photoInput) {
    photoInput.addEventListener('change', function(e) {
        if (e.target.files?.[0]) {
            const file = e.target.files[0];
            const maxSize = 1 * 1024 * 1024; // 1 MB

            if (file.size > maxSize) {
                showFlashMessage('The selected file is too large. Please choose a file smaller than 1 MB.', 'warning');
                e.target.value = ''; // Clear the file input
                const preview = document.getElementById('photoPreview');
                preview.src = '';
                preview.style.display = 'none';
                return;
            }

            const reader = new FileReader();
            reader.onload = function(evt) {
                const preview = document.getElementById('photoPreview');
                preview.src = evt.target.result;
                preview.style.display = 'block';
                // Clear captured data if a file is selected
                document.getElementById('capturedPhotoData').value = '';
            };
            reader.readAsDataURL(file);
        }
    });
}

function closeCamera() {
    const overlay = document.getElementById('cameraOverlay');
    overlay.classList.add('d-none');

    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
    }
}
// --- End camera logic ---

function closeOffcanvas() {
    const offcanvasEl = document.getElementById('mobileSidebar');
    if (offcanvasEl) {
        const offcanvas = bootstrap.Offcanvas.getInstance(offcanvasEl);
        if (offcanvas) {
            offcanvas.hide();
        }
    }
}

function calculateDatePlusMonths(startDateStr, monthsStr) {
    if (!startDateStr || !monthsStr) return '';
    const date = new Date(startDateStr);
    if (Number.isNaN(date.getTime())) return '';

    const months = Number.parseInt(monthsStr.split(' ')[0]);
    if (Number.isNaN(months)) return '';

    date.setMonth(date.getMonth() + months);
    return date.toISOString().split('T')[0];
}

function calculateRenewEndDate() {
    const startDate = document.getElementById('renewSubscriptionStartDate').value;
    const plan = document.getElementById('renewSubscriptionPlan').value;
    const endDateField = document.getElementById('renewSubscriptionEndDate');

    if (startDate && plan) {
        const newEnd = calculateDatePlusMonths(startDate, plan);
        if (newEnd) {
            endDateField.value = newEnd;
        }
    }
}

function showSection(sectionId, event) {
    if (event) event.preventDefault();

    // If navigating away from register, clear it (unless editing)
    const mobileNumField = document.getElementById('mobile_number');
    if (sectionId !== 'register' && mobileNumField?.hasAttribute('readonly')) {
        resetForm();
    }

    // Hide all sections
    const sections = document.querySelectorAll('.section');
    sections.forEach(section => {
        section.classList.remove('active');
    });

    // Remove active class from all buttons
    const buttons = document.querySelectorAll('.sidebar-btn');
    buttons.forEach(btn => {
        btn.classList.remove('active');
    });

    // Show the selected section
    document.getElementById(sectionId).classList.add('active');

    // Add active class to corresponding buttons (both desktop and mobile menus)
    document.querySelectorAll(`.sidebar-btn[onclick*="showSection('${sectionId}'"]`).forEach(b => b.classList.add('active'));

    // Set joining date to today if we are opening the register section and not editing
    if (sectionId === 'register' && mobileNumField && !mobileNumField.hasAttribute('readonly')) {
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('joining_date').value = today;
    }
}

function filterMembers(status) {
    // Switch to the members section
    showSection('members');

    // Update the radio button selection
    if (status === 'active') {
        document.getElementById('filterActive').checked = true;
    } else if (status === 'expired') {
        document.getElementById('filterExpired').checked = true;
    } else {
        document.getElementById('filterAll').checked = true;
    }

    // Apply the filter
    applyMemberFilter();
}

function applyMemberFilter() {
    const mobileSearchInput = document.getElementById('mobileSearch');
    if (!mobileSearchInput) return; // members filter not shown to members
    const textFilter = mobileSearchInput.value.toUpperCase();

    let statusFilter = '';
    if (document.getElementById('filterActive')?.checked) {
        statusFilter = 'active';
    } else if (document.getElementById('filterExpired')?.checked) {
        statusFilter = 'expired';
    }

    const table = document.getElementById('membersTable');
    const tr = table.getElementsByTagName('tr');

    for (let i = 1; i < tr.length; i++) {
        const mobileTd = tr[i].getElementsByTagName('td')[1];
        const statusTd = tr[i].querySelector('.status-cell');

        if (mobileTd && statusTd) {
            const mobileValue = mobileTd.textContent || mobileTd.innerText;
            const statusValue = statusTd.dataset.status || '';

            const matchesText = mobileValue.toUpperCase().includes(textFilter);
            const matchesStatus = (statusFilter === '') || (statusFilter === statusValue);

            if (matchesText && matchesStatus) {
                tr[i].style.display = "";
            } else {
                tr[i].style.display = "none";
            }
        }
    }
}

function searchByMobile() {
    applyMemberFilter();
}

function getFilterValues() {
    const searchInput = document.getElementById('transactionSearch');
    const textFilter = searchInput ? searchInput.value.toUpperCase() : '';
    const fromDateStr = document.getElementById('transactionFromDate').value;
    const toDateStr = document.getElementById('transactionToDate').value;
    const fromDate = fromDateStr ? new Date(fromDateStr) : null;
    const toDate = toDateStr ? new Date(toDateStr) : null;
    return { textFilter, fromDate, toDate };
}

function matchesTextFilter(mobileValue, textFilter) {
    if (currentUserRole !== 'admin') return true;
    return mobileValue.toUpperCase().includes(textFilter);
}

function matchesDateFilter(txnDate, fromDate, toDate) {
    if (!fromDate && !toDate) return true;
    if (Number.isNaN(txnDate.getTime())) return false;
    if (fromDate && txnDate < fromDate) return false;
    if (toDate && txnDate > toDate) return false;
    return true;
}

function matchesFilters(tr, filters) {
    const mobileTd = tr.querySelector('.txn-mobile-cell');
    const dateTd = tr.querySelector('.txn-date-cell');

    if (!mobileTd || !dateTd) return false;

    const mobileValue = mobileTd.textContent || mobileTd.innerText;
    const dateValueStr = dateTd.textContent || dateTd.innerText;
    const txnDate = new Date(dateValueStr);

    const textMatch = matchesTextFilter(mobileValue, filters.textFilter);
    const dateMatch = matchesDateFilter(txnDate, filters.fromDate, filters.toDate);

    return textMatch && dateMatch;
}

function filterTransactions() {
    const filters = getFilterValues();
    const table = document.getElementById('transactionsTable');
    const trs = table.getElementsByTagName('tr');

    for (let i = 1; i < trs.length; i++) {
        trs[i].style.display = matchesFilters(trs[i], filters) ? "" : "none";
    }
}

function searchTransactionsByMobile() {
    filterTransactions();
}

function clearTransactionFilters() {
    const searchInput = document.getElementById('transactionSearch');
    if (searchInput) searchInput.value = '';
    document.getElementById('transactionFromDate').value = '';
    document.getElementById('transactionToDate').value = '';
    filterTransactions();
}

function showLoading() {
    document.getElementById('loadingOverlay').classList.remove('d-none');
}

function hideLoading() {
    document.getElementById('loadingOverlay').classList.add('d-none');
}

function populateMemberView(data) {
    currentMemberData = data; // Save for editing

    // Populate data in the view section
    document.getElementById('viewFirstName').innerText = data.first_name || 'N/A';
    document.getElementById('viewLastName').innerText = data.last_name || 'N/A';
    document.getElementById('viewMobileNumber').innerText = data.mobile_number || 'N/A';
    document.getElementById('viewEmail').innerText = data.email || 'N/A';
    document.getElementById('viewGender').innerText = data.gender || 'N/A';
    document.getElementById('viewAddress').innerText = data.address || 'N/A';
    document.getElementById('viewDob').innerText = data.dob || 'N/A';
    document.getElementById('viewJoiningDate').innerText = data.joining_date || 'N/A';
    document.getElementById('viewSubscription').innerText = data.subscription || 'N/A';
    document.getElementById('viewSubscriptionStart').innerText = data.subscription_start_date || 'N/A';
    document.getElementById('viewSubscriptionEnd').innerText = data.subscription_end_date || 'N/A';

    const badgeEl = document.getElementById('viewStatusBadge');
    badgeEl.className = 'badge';
    if (data.status === 'active') {
        badgeEl.innerText = 'Active';
        badgeEl.classList.add('bg-success');
    } else {
        badgeEl.innerText = data.status || 'Unknown';
        badgeEl.classList.add('bg-secondary');
    }

    document.getElementById('vitalHeight').value = data.height || '';
    document.getElementById('vitalWeight').value = data.weight || '';
    document.getElementById('vitalBmi').value = data.bmi || '';

    // Populate Renew Subscription form defaults
    if (document.getElementById('renewSubscriptionPlan')) {
        document.getElementById('renewSubscriptionPlan').value = data.subscription || '1 Month';
    }

    // Set default renew start date to today, or the end date if it's in the future
    if (document.getElementById('renewSubscriptionStartDate')) {
        let defaultRenewDate = new Date().toISOString().split('T')[0];
        if (data.subscription_end_date) {
            const endDate = new Date(data.subscription_end_date);
            if (endDate > new Date()) {
                defaultRenewDate = data.subscription_end_date;
            }
        }
        document.getElementById('renewSubscriptionStartDate').value = defaultRenewDate;
        calculateRenewEndDate();

        // clear out the amount field for a fresh renewal
        document.getElementById('renewAmount').value = '0';
        document.getElementById('renewDiscount').value = '';
        document.getElementById('renewPaymentMethod').value = 'Credit Card';
    }

    // Handle Photo display
    const photoEl = document.getElementById('viewPhoto');
    const noPhotoEl = document.getElementById('noPhoto');
    if (data.photo) {
        photoEl.src = addCacheBuster(data.photo); // Apply cache busting
        photoEl.classList.remove('d-none');
        noPhotoEl.classList.add('d-none');
    } else {
        photoEl.classList.add('d-none');
        noPhotoEl.classList.remove('d-none');
    }

    // Setup Edit Button
    const editBtn = document.getElementById('editMemberBtn');
    if (editBtn) {
        editBtn.onclick = () => editMember();
    }
}

async function viewMember(mobileNumber) {
    if (currentMember && currentMember.mobile_number === mobileNumber) {
        populateMemberView(currentMember);
        showSection('viewMemberDetails');
        return;
    }
    showLoading();
    try {
        const response = await fetch(`/api/member/${mobileNumber}`);
        if (!response.ok) {
            showFlashMessage('Member not found', 'danger');
            return;
        }
        const data = await response.json();
        populateMemberView(data);
        showSection('viewMemberDetails');
    } catch (error) {
        console.error('Error fetching member details:', error);
        showFlashMessage('Error loading member details.', 'danger');
    } finally {
        hideLoading();
    }
}

function calculateBMI() {
    const height = Number.parseFloat(document.getElementById('vitalHeight').value);
    const weight = Number.parseFloat(document.getElementById('vitalWeight').value);
    if (height && weight && height > 0) {
        // BMI = weight(kg) / (height(m) * height(m))
        const heightInMeters = height / 100;
        const bmi = weight / (heightInMeters * heightInMeters);
        document.getElementById('vitalBmi').value = bmi.toFixed(2);
    } else {
        document.getElementById('vitalBmi').value = '';
    }
}

async function updateVitals(event) {
    event.preventDefault();
    if (!currentMemberData) return;

    const height = document.getElementById('vitalHeight').value;
    const weight = document.getElementById('vitalWeight').value;
    const bmi = document.getElementById('vitalBmi').value;
    const mobileNumber = currentMemberData.mobile_number;

    showLoading();
    try {
        const formData = new FormData();
        formData.append('mobile_number', mobileNumber);
        formData.append('height', height);
        formData.append('weight', weight);
        formData.append('bmi', bmi);

        const response = await fetch('/update_vitals', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            showFlashMessage('Vitals updated successfully!', 'success');
            viewMember(mobileNumber); // Reload to get updated data
        } else {
            showFlashMessage('Failed to update vitals.', 'danger');
        }
    } catch (error) {
        console.error('Error updating vitals:', error);
        showFlashMessage('An error occurred while updating vitals.', 'danger');
    } finally {
        hideLoading();
    }
}

async function renewSubscription(event) {
    event.preventDefault();
    if (!currentMemberData) return;

    const plan = document.getElementById('renewSubscriptionPlan').value;
    const startDate = document.getElementById('renewSubscriptionStartDate').value;
    const endDate = document.getElementById('renewSubscriptionEndDate').value;
    const amount = document.getElementById('renewAmount').value;
    const discount = document.getElementById('renewDiscount').value;
    const paymentMethod = document.getElementById('renewPaymentMethod').value;
    const mobileNumber = currentMemberData.mobile_number;

    showLoading();
    try {
        const formData = new FormData();
        formData.append('mobile_number', mobileNumber);
        formData.append('subscription', plan);
        formData.append('subscription_start_date', startDate);
        formData.append('subscription_end_date', endDate);
        formData.append('amount', amount);
        formData.append('discount', discount);
        formData.append('payment_method', paymentMethod);

        const response = await fetch('/renew_subscription', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            showFlashMessage('Subscription renewed successfully! A new transaction has been recorded.', 'success');
            viewMember(mobileNumber); // Reload to get updated data
            // Also trigger a background reload of transactions just in case the user switches tabs
            fetch('/fitmafia').then(() => {});
        } else {
            showFlashMessage('Failed to renew subscription.', 'danger');
        }
    } catch (error) {
        console.error('Error renewing subscription:', error);
        showFlashMessage('An error occurred while renewing subscription.', 'danger');
    } finally {
        hideLoading();
    }
}

function editMember() {
    if (!currentMemberData) return;

    // Populate the form with currentMemberData
    document.getElementById('memberForm').action = '/update_member';
    document.getElementById('firstName').value = currentMemberData.first_name || '';
    const lastNameField = document.getElementById('lastName');
    if (lastNameField) {
        lastNameField.value = currentMemberData.last_name || '';
    }
    document.getElementById('mobile_number').value = currentMemberData.mobile_number || '';
    document.getElementById('mobile_number').setAttribute('readonly', true); // Prevent PK change
    document.getElementById('email').value = currentMemberData.email || '';
    if (currentUserRole === 'member') {
         document.getElementById('email').setAttribute('readonly', true);
    }

    // Set password to the actual password and make it not required for submission
    const passwordField = document.getElementById('password');
    passwordField.value = currentMemberData.password || '';
    passwordField.removeAttribute('required');

    document.getElementById('gender').value = currentMemberData.gender || '';
    document.getElementById('address').value = currentMemberData.address || '';
    document.getElementById('dob').value = currentMemberData.dob || '';
    document.getElementById('joining_date').value = currentMemberData.joining_date || '';

    // If editing, hide the terms block since they've already accepted
    document.getElementById('termsContainer').style.display = 'none';
    document.getElementById('termsAccepted').removeAttribute('required');

    // Handle Photo Preview when editing
    const preview = document.getElementById('photoPreview');
    if (currentMemberData.photo) {
        preview.src = addCacheBuster(currentMemberData.photo); // Apply cache busting
        preview.style.display = 'block';
    } else {
        preview.style.display = 'none';
    }
    document.getElementById('capturedPhotoData').value = '';

    // Change Title & Buttons
    document.getElementById('registerFormTitle').innerText = "Edit Member Details";
    document.getElementById('submitBtn').innerText = "Update Member";
    document.getElementById('cancelEditBtn').classList.remove('d-none');

    // Show the registration form
    showSection('register');
}

function resetForm(event) {
    // Reset form fields
    document.getElementById('memberForm').reset();
    document.getElementById('memberForm').action = '/register_member';
    document.querySelectorAll('#memberForm .is-invalid').forEach(el => el.classList.remove('is-invalid'));

    // Remove readonly from mobile number
    document.getElementById('mobile_number').removeAttribute('readonly');
    document.getElementById('email').removeAttribute('readonly');
    document.getElementById('password').setAttribute('required', 'true');

    // Reset password visibility
    const passwordField = document.getElementById('password');
    passwordField.setAttribute('type', 'password');
    const toggleIcon = document.getElementById('togglePassword').querySelector('i');
    toggleIcon.classList.remove('bi-eye');
    toggleIcon.classList.add('bi-eye-slash');

    // Show terms block for new registrations
    document.getElementById('termsContainer').style.display = 'block';
    document.getElementById('termsAccepted').setAttribute('required', 'true');

    // Hide preview and clear hidden input
    document.getElementById('photoPreview').style.display = 'none';
    document.getElementById('capturedPhotoData').value = '';

    // Reset UI labels and buttons
    document.getElementById('registerFormTitle').innerText = "New Member Registration";
    document.getElementById('submitBtn').innerText = "Register Member";
    document.getElementById('cancelEditBtn').classList.add('d-none');
    currentMemberData = null;

    // Reset joining date to today when canceling
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('joining_date').value = today;

    // If called explicitly via Cancel button, go back to Member list or Dashboard
    if(event?.target.id === 'cancelEditBtn') {
        if (currentUserRole === 'admin') {
            showSection('members');
        } else {
            showSection('viewMemberDetails');
        }
    }
}

function viewMemberTransactions() {
    if (!currentMemberData) return;
    showSection('transactions');

    const searchInput = document.getElementById('transactionSearch');
    if (searchInput) {
        searchInput.value = currentMemberData.mobile_number;
    }
    document.getElementById('transactionFromDate').value = '';
    document.getElementById('transactionToDate').value = '';

    filterTransactions();
}

function validateAndHighlight(field, condition) {
    if (condition) {
        field.classList.remove('is-invalid');
        return true;
    } else {
        field.classList.add('is-invalid');
        return false;
    }
}

async function handleMemberFormSubmit(event) {
    event.preventDefault();

    const memberForm = document.getElementById('memberForm');
    const url = memberForm.action;
    let isValid = true;

    // --- Validation for new member registration ---
    if (url.endsWith('register_member')) {
        const firstNameField = document.getElementById('firstName');
        const mobileNumberField = document.getElementById('mobile_number');
        const passwordField = document.getElementById('password');
        const genderField = document.getElementById('gender');
        const dobField = document.getElementById('dob');
        const emailField = document.getElementById('email');
        const addressField = document.getElementById('address');
        const termsAcceptedField = document.getElementById('termsAccepted');

        isValid &= validateAndHighlight(firstNameField, firstNameField.value.trim() !== '');
        isValid &= validateAndHighlight(mobileNumberField, /^\d{10}$/.test(mobileNumberField.value));
        isValid &= validateAndHighlight(passwordField, passwordField.value.length >= 4);
        isValid &= validateAndHighlight(genderField, genderField.value !== '');
        if (termsAcceptedField?.hasAttribute('required')) {
            isValid &= validateAndHighlight(termsAcceptedField, termsAcceptedField.checked);
        }

        // Optional fields: validate format only if provided, clear invalid state otherwise
        if (emailField) {
            if (emailField.value.trim() !== '') {
                isValid &= validateAndHighlight(emailField, emailField.checkValidity());
            } else {
                emailField.classList.remove('is-invalid');
            }
        }
        if (dobField) {
            dobField.classList.remove('is-invalid');
        }
        if (addressField) {
            addressField.classList.remove('is-invalid');
        }

        if (!isValid) {
            showFlashMessage('fill in all required fields', 'danger');
            return;
        }
    }
    // --- End of validation ---

    const formData = new FormData(memberForm);
    showLoading();

    try {
        const response = await fetch(url, { method: 'POST', body: formData });
        const result = await response.json();
        if (result.redirect) {
            globalThis.location.href = result.redirect;
            return;
        }

        showFlashMessage(result.message, result.status);

        if (result.status === 'success') {
            if (url.endsWith('register_member')) {
                const mobileNumber = formData.get('mobile_number');
                viewMember(mobileNumber);
                resetForm();
            } else {
                const mobileNumber = formData.get('mobile_number');
                viewMember(mobileNumber);
            }
        }

    } catch (error) {
        console.error('Error:', error);
        showFlashMessage('An error occurred. Please try again.', 'danger');
    } finally {
        hideLoading();
    }
}

function togglePasswordVisibility() {
    const password = document.getElementById('password');
    const toggleBtn = document.getElementById('togglePassword');
    if (!password || !toggleBtn) return;
    const icon = toggleBtn.querySelector('i');
    const type = password.getAttribute('type') === 'password' ? 'text' : 'password';
    password.setAttribute('type', type);
    icon.classList.toggle('bi-eye');
    icon.classList.toggle('bi-eye-slash');
}

// --- Member Deletion with Reverification ---
let memberToDelete = null;

function openDeleteMemberModal(mobileNumber, memberName) {
    if (!mobileNumber) return;

    memberToDelete = {
        mobileNumber: String(mobileNumber).trim(),
        memberName: memberName ? String(memberName).trim() : String(mobileNumber).trim()
    };

    const nameEl = document.getElementById('deleteModalMemberName');
    const mobileEl = document.getElementById('deleteModalMemberMobile');
    const inputEl = document.getElementById('deleteReverifyInput');
    const confirmBtn = document.getElementById('confirmDeleteMemberBtn');

    if (nameEl) nameEl.textContent = memberToDelete.memberName || 'Member';
    if (mobileEl) mobileEl.textContent = memberToDelete.mobileNumber;
    if (inputEl) {
        inputEl.value = '';
        inputEl.classList.remove('is-valid', 'is-invalid');
    }
    if (confirmBtn) confirmBtn.disabled = true;

    const modalEl = document.getElementById('deleteMemberModal');
    if (modalEl && window.bootstrap) {
        const modalInstance = bootstrap.Modal.getOrCreateInstance(modalEl);
        modalInstance.show();
        setTimeout(() => inputEl?.focus(), 400);
    }
}

function checkDeleteReverify() {
    if (!memberToDelete) return;
    const inputEl = document.getElementById('deleteReverifyInput');
    const confirmBtn = document.getElementById('confirmDeleteMemberBtn');
    if (!inputEl || !confirmBtn) return;

    const val = inputEl.value.trim();
    const isMatched = (val === memberToDelete.mobileNumber || val.toUpperCase() === 'DELETE');

    if (isMatched) {
        inputEl.classList.add('is-valid');
        inputEl.classList.remove('is-invalid');
        confirmBtn.disabled = false;
    } else {
        inputEl.classList.remove('is-valid');
        confirmBtn.disabled = true;
    }
}

async function executeDeleteMember() {
    if (!memberToDelete) return;
    const { mobileNumber, memberName } = memberToDelete;

    const inputEl = document.getElementById('deleteReverifyInput');
    const val = inputEl ? inputEl.value.trim() : '';
    if (val !== mobileNumber && val.toUpperCase() !== 'DELETE') {
        showFlashMessage('Please reverify the deletion by typing the mobile number or DELETE.', 'danger');
        return;
    }

    const modalEl = document.getElementById('deleteMemberModal');
    if (modalEl && window.bootstrap) {
        const modalInstance = bootstrap.Modal.getInstance(modalEl);
        modalInstance?.hide();
    }

    showLoading();
    try {
        const response = await fetch(`/delete_member/${encodeURIComponent(mobileNumber)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const result = await response.json();
        if (result.status === 'success') {
            showFlashMessage(result.message || `Member ${memberName} deleted successfully.`, 'success');

            // Remove table row
            const row = document.getElementById(`member-row-${mobileNumber}`) ||
                        document.querySelector(`tr[data-mobile="${mobileNumber}"]`);
            if (row) {
                const statusCell = row.querySelector('.status-cell');
                const wasActive = statusCell && statusCell.dataset.status === 'active';

                row.remove();

                // Update summary dashboard card counters
                const countCards = document.querySelectorAll('.card-text.fs-2');
                if (countCards.length >= 3) {
                    const totalCard = countCards[0];
                    const activeCard = countCards[1];
                    const inactiveCard = countCards[2];

                    const total = parseInt(totalCard.textContent, 10);
                    if (!isNaN(total) && total > 0) totalCard.textContent = total - 1;

                    if (wasActive) {
                        const active = parseInt(activeCard.textContent, 10);
                        if (!isNaN(active) && active > 0) activeCard.textContent = active - 1;
                    } else {
                        const inactive = parseInt(inactiveCard.textContent, 10);
                        if (!isNaN(inactive) && inactive > 0) inactiveCard.textContent = inactive - 1;
                    }
                }
            }

            // Return to member list if currently viewing deleted member
            const currentActive = document.querySelector('.section.active');
            if (currentActive?.id === 'viewMemberDetails' && currentMemberData?.mobile_number === mobileNumber) {
                currentMemberData = null;
                showSection('members');
            }
        } else {
            showFlashMessage(result.message || 'Failed to delete member.', 'danger');
        }
    } catch (error) {
        console.error('Error deleting member:', error);
        showFlashMessage('An error occurred while deleting member.', 'danger');
    } finally {
        hideLoading();
        memberToDelete = null;
    }
}


//on load function
document.addEventListener('DOMContentLoaded', () => {
    const togglePassword = document.getElementById('togglePassword');
    if (togglePassword) {togglePassword.addEventListener('click', togglePasswordVisibility);}

    if (currentUserRole === 'member' && currentUserName) {
        if (currentMember) { populateMemberView(currentMember); }
        else { viewMember(currentUserName); }
        filterTransactions();}

    else {
        const currentActive = document.querySelector('.section.active');
        if (currentActive?.id === 'register') {
            const joiningDateField = document.getElementById('joining_date');
            if (joiningDateField) {
                const today = new Date().toISOString().split('T')[0];
                joiningDateField.value = today;
            }
        }
    }

    document.getElementById('submitBtn').addEventListener('click', handleMemberFormSubmit);

    const deleteReverifyInput = document.getElementById('deleteReverifyInput');
    if (deleteReverifyInput) {
        deleteReverifyInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                const confirmBtn = document.getElementById('confirmDeleteMemberBtn');
                if (confirmBtn && !confirmBtn.disabled) {
                    executeDeleteMember();
                }
            }
        });
    }

    autoCloseFlashes();
});
