function [in] = aef2aep(in)
in = (exp(in)-1)./exp(in);
end