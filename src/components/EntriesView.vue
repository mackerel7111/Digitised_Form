<script setup>
defineProps({
  selectedForm: {
    type: Object,
    required: true,
  },
  selectedSubmissions: {
    type: Array,
    required: true,
  },
  backToDashboard: {
    type: Function,
    required: true,
  },
  downloadSubmissionPdf: {
    type: Function,
    required: true,
  },
})
</script>

<template>
  <div class="d-flex flex-column flex-lg-row justify-content-between gap-3 mb-4">
    <div>
      <p class="text-uppercase fw-bold text-secondary small mb-2">Saved Entries</p>
      <h1 class="h2 fw-bold mb-2">{{ selectedForm.name }}</h1>
      <p class="text-secondary mb-0">Download filled PDFs from previously saved form entries.</p>
    </div>

    <div class="d-flex align-items-start">
      <button class="btn btn-outline-secondary" type="button" @click="backToDashboard">
        Back to Forms
      </button>
    </div>
  </div>

  <section class="card border-0 shadow-sm">
    <div class="card-header bg-white py-3">
      <h2 class="h5 mb-1">Entries</h2>
      <p class="text-secondary mb-0">Saved submissions for this published template.</p>
    </div>

    <div v-if="selectedSubmissions.length === 0" class="card-body text-center py-5">
      <h3 class="h6 mb-2">No saved entries yet</h3>
      <p class="text-secondary mb-0">Fill this form and click Save Entry to create one.</p>
    </div>

    <div v-else class="list-group list-group-flush">
      <div
        v-for="submission in selectedSubmissions"
        :key="submission.id"
        class="list-group-item d-flex flex-column flex-md-row justify-content-between gap-3 py-3"
      >
        <div>
          <h3 class="h6 mb-1">Entry {{ submission.id.slice(0, 8) }}</h3>
          <p class="text-secondary small mb-0">
            Saved {{ new Date(submission.createdAt).toLocaleString() }}
          </p>
        </div>

        <div class="d-flex align-items-center gap-2">
          <button
            class="btn btn-outline-success btn-sm"
            type="button"
            @click="downloadSubmissionPdf(submission)"
          >
            Download PDF
          </button>
        </div>
      </div>
    </div>
  </section>
</template>
