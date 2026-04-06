import { Check } from "lucide-react";

const STEPS = ["Template", "Documents", "Variables", "Review"];

interface WizardStepIndicatorProps {
  currentStep: number;
  completedSteps: number[];
}

export function WizardStepIndicator({
  currentStep,
  completedSteps,
}: WizardStepIndicatorProps) {
  return (
    <div className="flex items-center justify-center gap-0 h-12">
      {STEPS.map((label, index) => {
        const stepNum = index + 1;
        const isActive = stepNum === currentStep;
        const isCompleted = completedSteps.includes(stepNum);

        return (
          <div key={label} className="flex items-center">
            <div className="flex flex-col items-center">
              {/* Dot */}
              <div
                className={`flex items-center justify-center rounded-full ${
                  isCompleted
                    ? "w-5 h-5 bg-[oklch(0.55_0.2_142)]"
                    : isActive
                      ? "w-2 h-2 bg-primary"
                      : "w-2 h-2 bg-border"
                }`}
              >
                {isCompleted && (
                  <Check className="w-2.5 h-2.5 text-white" strokeWidth={3} />
                )}
              </div>
              {/* Label */}
              <span
                className={`text-[12px] mt-1 ${
                  isActive
                    ? "font-semibold text-foreground"
                    : "font-normal text-muted-foreground"
                }`}
              >
                {label}
              </span>
            </div>
            {/* Connector line */}
            {index < STEPS.length - 1 && (
              <div className="w-6 h-[2px] bg-border mx-2 -mt-4" />
            )}
          </div>
        );
      })}
    </div>
  );
}
