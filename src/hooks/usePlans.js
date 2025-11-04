import { useState, useEffect } from 'react';

// Mock data structured to match the backend's StudyPlanEvaluation model
// plus extra detail fields needed for the frontend display and editing.
const MOCK_PLANS = [
  {
    planId: 'plan-001',
    studentName: 'Alice Johnson (Math Major)',
    course: 'Advanced Calculus',
    semester: 'Fall 2025',
    scheduling_score: 70, // YELLOW
    alignment_score: 85, // GREEN
    workload_score: 55, // YELLOW
    weighted_color: 'yellow',
    scheduling_reasoning: 'The student scheduled PHY-101 and BUS-101 exams on the same day (May 1st) in separate slots, which creates an elevated risk of stress and poor performance. This is the main scheduling concern.',
    alignment_reasoning: 'All selected courses (MTH-110, MTH-215, PHY-101) are highly relevant to the Mathematics major core curriculum.',
    overall_recommendation: 'The plan is borderline. Review the May 1st exam conflict. Consider suggesting the student request a deferral for one of the exams to reduce stress.',
    study_plan_details: [
      { courseCode: 'MTH-110', courseName: 'Calculus I', allocatedHours: 10, priority: 'High' },
      { courseCode: 'MTH-215', courseName: 'Linear Algebra', allocatedHours: 8, priority: 'High' },
      { courseCode: 'PHY-101', courseName: 'Classical Mechanics', allocatedHours: 12, priority: 'High' },
      { courseCode: 'BUS-101', courseName: 'Intro to Business', allocatedHours: 5, priority: 'Medium' },
    ],
  },
  {
    planId: 'plan-002',
    studentName: 'Bob Smith (CS Major)',
    course: 'Database Management',
    semester: 'Fall 2025',
    scheduling_score: 80, // GREEN
    alignment_score: 60, // YELLOW
    workload_score: 65, // YELLOW
    weighted_color: 'yellow',
    scheduling_reasoning: 'The schedule is balanced with adequate time between lectures and exams. No immediate time conflicts were found.',
    alignment_reasoning: 'CSC-310 (Database Systems) is core, but the student is taking HRM-200 (HR Management), which has no clear link to the Computer Science degree. This is impacting the alignment score.',
    overall_recommendation: 'The plan is generally safe. The alignment is questioned due to one outlier course (HRM-200). Human review should confirm if HRM-200 is being taken for a minor or elective credit.',
    study_plan_details: [
      { courseCode: 'CSC-310', courseName: 'Database Systems', allocatedHours: 15, priority: 'High' },
      { courseCode: 'CSC-250', courseName: 'Data Structures', allocatedHours: 15, priority: 'High' },
      { courseCode: 'HRM-200', courseName: 'HR Management', allocatedHours: 4, priority: 'Low' },
    ],
  },
];

const usePlans = () => {
  const [plans, setPlans] = useState(MOCK_PLANS);
  const [loading, setLoading] = useState(false);

  // Simulate fetching data from the API
  useEffect(() => {
    // In a real app, this would be a fetch call:
    // fetch('/api/hitl-queue').then(res => setPlans(res.json()));
    setLoading(true);
    const timer = setTimeout(() => {
      setLoading(false);
    }, 500);
    return () => clearTimeout(timer);
  }, []);

  // Simulates sending the human's decision back to the LangGraph thread
  const submitDecision = async (planId, decision, context = '', editedDetails = null) => {
    setLoading(true);
    console.log(`Submitting decision for ${planId}: ${decision}`);
    console.log('Context:', context);
    if (editedDetails) {
      console.log('Edited Plan Details:', editedDetails);
      // In a real app, you would send a POST request with this payload:
      /*
      {
        thread_id: planId, // Assuming planId is the thread_id
        decision: 'edit',
        context: context,
        plan_patch: editedDetails,
      }
      */
    } else {
       // In a real app, you would send a POST request with this payload:
      /*
      {
        thread_id: planId,
        decision: decision, // 'approve' or 'reject'
      }
      */
    }

    // Simulate API latency
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Remove the plan from the local queue after submission
    setPlans(currentPlans => currentPlans.filter(p => p.planId !== planId));
    setLoading(false);
  };

  return { plans, loading, submitDecision };
};

export { usePlans };
