import React, { useState, useEffect } from 'react';
import { usePlans } from '../hooks/usePlans';
import { Clock, BookOpen, AlertTriangle, CheckCircle, XCircle, Save } from 'lucide-react';

// Simplified Modal Component for capturing edit context
const EditContextModal = ({ isOpen, onClose, onSubmit }) => {
  const [context, setContext] = useState('');

  if (!isOpen) return null;

  const handleSubmit = () => {
    onSubmit(context);
    setContext('');
  };

  return (
    <div className="fixed inset-0 bg-gray-900 bg-opacity-75 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg p-6 space-y-4">
        <h3 className="text-xl font-semibold text-gray-800">Submit Edited Plan Context</h3>
        <p className="text-sm text-gray-600">Please provide a brief justification for the edits made. This context will be sent back to the AI for final processing.</p>
        <textarea
          className="w-full h-24 p-3 border border-gray-300 rounded-lg focus:ring-amber-500 focus:border-amber-500"
          placeholder="e.g., I reduced the allocated hours for MTH-300 to address the workload score and confirmed the FIN-410 prerequisite will be waived."
          value={context}
          onChange={(e) => setContext(e.target.value)}
        />
        <div className="flex justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!context.trim()}
            className={`px-4 py-2 text-sm font-medium text-white rounded-lg transition ${
              context.trim()
                ? 'bg-amber-600 hover:bg-amber-700'
                : 'bg-amber-300 cursor-not-allowed'
            }`}
          >
            Submit Edits
          </button>
        </div>
      </div>
    </div>
  );
};

// Main Dashboard Component
const ReviewDashboard = () => {
  const { plans, loading, submitDecision } = usePlans();
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [editedPlanDetails, setEditedPlanDetails] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // NOTE: Editing is permanently enabled for the staff/human reviewer.
  const isEditing = true;

  // Set the first plan as selected when the list loads
  useEffect(() => {
    if (plans.length > 0 && !selectedPlan) {
      setSelectedPlan(plans[0]);
    } else if (plans.length > 0 && selectedPlan) {
      // Keep selected plan if it still exists, otherwise select first
      const current = plans.find(p => p.planId === selectedPlan.planId);
      if (!current) {
          setSelectedPlan(plans[0]);
      } else {
          setSelectedPlan(current);
      }
    } else if (plans.length === 0) {
      setSelectedPlan(null);
    }
  }, [plans]);

  // Sync details when a new plan is selected
  useEffect(() => {
    if (selectedPlan) {
      // Deep copy study_plan_details for editing
      setEditedPlanDetails(selectedPlan.study_plan_details.map(d => ({ ...d })));
    }
  }, [selectedPlan]);

  const getScoreColor = (score) => {
    if (score <= 45) return 'text-red-500 bg-red-50';
    if (score <= 75) return 'text-amber-600 bg-amber-50';
    return 'text-green-600 bg-green-50';
  };

  // Helper to determine the button color based on the weighted color code
  const getButtonColorClass = (colorCode) => {
      switch (colorCode.toLowerCase()) {
          case 'red':
              return 'bg-red-600 hover:bg-red-700';
          case 'yellow':
              return 'bg-amber-600 hover:bg-amber-700';
          case 'green':
              return 'bg-green-600 hover:bg-green-700';
          default:
              return 'bg-gray-500 hover:bg-gray-600';
      }
  };

  const handleDetailChange = (index, field, value) => {
    const newDetails = [...editedPlanDetails];
    newDetails[index][field] = field === 'allocatedHours' ? parseInt(value) || 0 : value;
    setEditedPlanDetails(newDetails);
  };

  const handleDecision = async (decision) => {
    if (!selectedPlan) return;

    if (decision === 'edit') {
      setIsModalOpen(true);
      return;
    }

    try {
      await submitDecision(selectedPlan.planId, decision);
      // NOTE: Using window.alert for simplicity in this sandbox environment
      window.alert(`${selectedPlan.studentName}'s plan was marked as ${decision}. It has been removed from your queue.`);
    } catch (e) {
      window.alert(`Error submitting decision: ${e.message}`);
    }
  };

  const handleModalSubmit = async (context) => {
    setIsModalOpen(false);
    try {
      // Submits the 'edit' decision along with the edited details and context
      await submitDecision(selectedPlan.planId, 'edit', context, editedPlanDetails);
      window.alert(`${selectedPlan.studentName}'s plan was edited and submitted. It has been removed from your queue.`);
    } catch (e) {
      window.alert(`Error submitting edits: ${e.message}`);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex font-sans">
      <EditContextModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleModalSubmit}
      />

      {/* Sidebar: Queue */}
      <div className="w-80 bg-white border-r border-gray-200 p-4 shadow-lg flex-shrink-0">
        <h2 className="text-2xl font-bold text-amber-600 mb-6 flex items-center">
          <AlertTriangle className="w-5 h-5 mr-2" /> Review Queue
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          {loading ? 'Loading...' : `${plans.length} Plans require review (YELLOW priority)`}
        </p>

        <div className="space-y-3 max-h-[80vh] overflow-y-auto">
          {plans.map(plan => (
            <div
              key={plan.planId}
              onClick={() => setSelectedPlan(plan)}
              className={`p-3 rounded-xl cursor-pointer transition duration-150 ease-in-out border ${
                selectedPlan?.planId === plan.planId
                  ? 'bg-amber-50 border-amber-500 ring-2 ring-amber-200'
                  : 'bg-gray-50 border-gray-200 hover:bg-gray-100'
              }`}
            >
              <p className="font-semibold text-gray-800">{plan.studentName}</p>
              <p className="text-xs text-gray-500">{plan.course} - {plan.semester}</p>
              <span className={`mt-1 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium text-white ${getButtonColorClass(plan.weighted_color)}`}>
                  {plan.weighted_color.toUpperCase()} - {Math.round((plan.scheduling_score * 0.4 + plan.alignment_score * 0.4 + plan.workload_score * 0.2))}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 p-8 overflow-auto">
        {!selectedPlan ? (
          <div className="text-center p-10 mt-20 text-gray-500">
            <CheckCircle className="w-10 h-10 mx-auto mb-4 text-green-500" />
            <p className="text-xl font-semibold">Queue Clear!</p>
            <p>No plans currently require Human-in-the-Loop review.</p>
          </div>
        ) : (
          <div className="space-y-8">
            <h1 className="text-3xl font-extrabold text-gray-900">
              Reviewing Plan for {selectedPlan.studentName} ({selectedPlan.course})
            </h1>
            <p className="text-lg text-gray-600">
              {selectedPlan.semester}
            </p>

            {/* AI Diagnosis and Scores */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Risk Score */}
              <div className="bg-white p-6 rounded-xl shadow-lg border-l-4 border-amber-500">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-lg text-amber-600">Overall AI Risk Score</h3>
                  <AlertTriangle className="w-6 h-6 text-amber-500" />
                </div>
                <div className="text-5xl font-extrabold mt-2 text-amber-500">
                  {Math.round((selectedPlan.scheduling_score * 0.4 + selectedPlan.alignment_score * 0.4 + selectedPlan.workload_score * 0.2))}
                </div>
                <p className="text-sm text-gray-500 mt-1">Weighted Average (40/40/20)</p>
              </div>

              {/* Component Scores */}
              {[
                { label: 'Scheduling Score', score: selectedPlan.scheduling_score, icon: Clock },
                { label: 'Alignment Score', score: selectedPlan.alignment_score, icon: BookOpen },
                { label: 'Workload Score', score: selectedPlan.workload_score, icon: AlertTriangle },
              ].map((item) => (
                <div key={item.label} className={`bg-white p-6 rounded-xl shadow-lg ${getScoreColor(item.score)}`}>
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-gray-700">{item.label}</h3>
                    <item.icon className="w-5 h-5" />
                  </div>
                  <div className="text-3xl font-extrabold mt-1">{item.score}</div>
                  <p className="text-sm text-gray-500 mt-1">Out of 100</p>
                </div>
              ))}
            </div>

            {/* AI Reasoning and Recommendation */}
            <div className="space-y-4">
              <div className="bg-white p-6 rounded-xl shadow-lg border-l-4 border-blue-500">
                <h3 className="font-bold text-lg text-blue-600 mb-2">Scheduling Agent Reasoning</h3>
                <p className="text-gray-700">{selectedPlan.scheduling_reasoning}</p>
              </div>
              <div className="bg-white p-6 rounded-xl shadow-lg border-l-4 border-indigo-500">
                <h3 className="font-bold text-lg text-indigo-600 mb-2">Alignment Agent Reasoning</h3>
                <p className="text-gray-700">{selectedPlan.alignment_reasoning}</p>
              </div>
              <div className="bg-white p-6 rounded-xl shadow-lg border-l-4 border-teal-500">
                <h3 className="font-bold text-lg text-teal-600 mb-2">Overall Recommendation</h3>
                <p className="text-gray-700">{selectedPlan.overall_recommendation}</p>
              </div>
            </div>


            {/* Study Plan Editor/Details */}
            <div className="bg-white p-6 rounded-xl shadow-lg">
              <div className="flex justify-between items-center mb-4">
                <h3 className="font-bold text-xl text-gray-800">Current Study Plan Details (Editable)</h3>
              </div>

              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Course Code</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Course Name</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-32">Allocated Hours/Week</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-24">Priority</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {editedPlanDetails.map((detail, index) => (
                      <tr key={detail.courseCode}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{detail.courseCode}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{detail.courseName}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <input
                            type="number"
                            min="0"
                            value={detail.allocatedHours}
                            onChange={(e) => handleDetailChange(index, 'allocatedHours', e.target.value)}
                            className="w-full border-gray-300 rounded-lg p-1 text-center focus:ring-amber-500 focus:border-amber-500"
                          />
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <select
                            value={detail.priority}
                            onChange={(e) => handleDetailChange(index, 'priority', e.target.value)}
                            className="w-full border-gray-300 rounded-lg p-1 focus:ring-amber-500 focus:border-amber-500"
                          >
                            <option>High</option>
                            <option>Medium</option>
                            <option>Low</option>
                          </select>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Human Decision Footer */}
            <div className="flex justify-end space-x-4 sticky bottom-0 bg-white p-4 border-t border-gray-200 rounded-xl shadow-2xl">
              {/* Reject button is always enabled */}
              <button
                onClick={() => handleDecision('reject')}
                disabled={loading}
                className={`flex items-center px-6 py-3 text-lg font-semibold text-white rounded-xl transition duration-150 shadow-md disabled:opacity-50 ${getButtonColorClass('red')}`}
              >
                <XCircle className="w-5 h-5 mr-2" /> Reject Plan (RED)
              </button>
              
              {/* Edit button triggers the modal to collect context before submission */}
              <button
                onClick={() => handleDecision('edit')}
                disabled={loading} // Since editing is permanent, this button submits the changes
                className={`flex items-center px-6 py-3 text-lg font-semibold text-white rounded-xl transition duration-150 shadow-md disabled:opacity-50 ${getButtonColorClass('yellow')}`}
              >
                <Save className="w-5 h-5 mr-2" /> Submit Edited Plan (YELLOW)
              </button>
              
              {/* Approve button is always enabled */}
              <button
                onClick={() => handleDecision('approve')}
                disabled={loading}
                className={`flex items-center px-6 py-3 text-lg font-semibold text-white rounded-xl transition duration-150 shadow-md disabled:opacity-50 ${getButtonColorClass('green')}`}
              >
                <CheckCircle className="w-5 h-5 mr-2" /> Final Approve (GREEN)
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ReviewDashboard;


